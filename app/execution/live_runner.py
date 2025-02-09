from __future__ import print_function
from builtins import range
import pyximport; pyximport.install()
from decimal import Decimal
import inspect
import os
import signal
import sys
import time

from delorean import Delorean
import importlib
import termcolor as tc

from execution.strategies.base import Strategy                                  #pyx file
from execution.harness.harness import Harness                                   #pyx file
from execution.lib import tick_profiling
from execution.lib.auditing import AuditException
from execution.lib.heartbeat import Heartbeat
from execution.lib.sentry import Sentry
from lib import session
from lib.logger import get_logger
from lib.models.mysql.event import EventRecorder
from lib.models.mysql.datum import DatumRecorder
from lib.util.time import humanize_seconds

logger = get_logger(__name__)

warm_shutdown_flag = False
restart_flag = False

BACKOFF_SECONDS_START = 10
BACKOFF_MULTIPLIER = 2



class NoStrategyClassFoundInModuleException(Exception):
    pass


def trigger_warm_shutdown(signal, frame):
    global warm_shutdown_flag
    logger.info(tc.colored('Setting Warm Shutdown Flag', 'red'))
    warm_shutdown_flag = True


def trigger_restart(signal, frame):
    global restart_flag
    logger.info(tc.colored('Setting Restart Flag', 'red'))
    restart_flag = True
    trigger_warm_shutdown(signal, frame)


signal.signal(signal.SIGINT, trigger_warm_shutdown)
signal.signal(signal.SIGHUP, trigger_restart)


def warm_shutdown(harness, db, sentry, execute):
    logger.info(tc.colored('Initiating Warm Shutdown', 'red'))

    try:
        if execute:
            harness.wind_down()

        logger.info(tc.colored('Warm Shutdown Complete', 'green'))
    except Exception as e:
        sentry.captureException()

        logger.exception(tc.colored(
            '[%s] %s' % (e.__class__.__name__, e.message),
            'red',
        ))

        logger.info(tc.colored(
            'Exception during warm shutdown, forcing shutdown',
            'red',
        ))


def restart():
    """
    execv replaces the current process with a new one which will reload the entire
    context (conf/code)--in this case, a new run of the exact same process. It abruptly
    ends the current process, so db connections, etc must be closed before running this.
    """

    logger.info(tc.colored('Restarting bot with new code/conf\n', 'green'))
    os.execv(sys.executable, [sys.executable] + sys.argv)


def gentle_sleep(seconds):
    """
    warm_shutdown_flag is triggered by ctrl-c. If the harness is in a sleep cycle we
    want to wake up so that we can shut down without a long delay.
    """

    for i in range(0, seconds):
        if warm_shutdown_flag:
            break

        time.sleep(1)


def get_strategy_class_from_module(module):
    """
    Get the strategy class from a module according to a simple ruleset.

    This ruleset is: return the first class defined in the module that is a subclass of
    the Strategy base class, and which case-insensitive matches the module name
    (filename) when any underscores are removed from the module name. This allows us to
    preserve the python convention of using CamelCase in class names and lower_case for
    module names.

    e.g.
        'simple_market_making.pyx' will match class 'SimpleMarketMaking'.
        'geminicoinbasearb.pyx' will match 'GeminCoinbaseArb'.
    """

    expected_strat_name = module.__name__.replace('_', '')

    if '.' in expected_strat_name:  # Probably a module path.
        expected_strat_name = expected_strat_name[expected_strat_name.rfind('.') + 1:]

    for x in dir(module):
        if x.lower() == expected_strat_name.lower():
            cls = getattr(module, x)

            if inspect.isclass(cls) and cls != Strategy and issubclass(cls, Strategy):
                return cls

    raise NoStrategyClassFoundInModuleException()


def get_builtin_strategy_class(strategy_name):
    """
    Load a strategy that ships with the Gryphon library.
    """

    path = 'gryphon.execution.strategies.builtin.%s' % strategy_name.lower()

    module = importlib.import_module(path)

    strategy_class = get_strategy_class_from_module(module)

    return strategy_class


def get_strategy_class_from_filepath(strategy_path):
    """
    Load a strategy that the library user has written and is specified as a filepath
    from the current working directory to a .pyx file.
    """

    module_path = strategy_path.replace('/', '.').replace('.pyx', '').replace('.py', '')

    # Since in this case we're importing a file outside of the library, we have to
    # add our current directory to the python path.
    sys.path.append(os.getcwd())

    module = importlib.import_module(module_path)
    strategy_class = get_strategy_class_from_module(module)

    return strategy_class


def get_strategy_class(strategy_path, builtin=False):
    if builtin is True:
        return get_builtin_strategy_class(strategy_path)
    else:
        return get_strategy_class_from_filepath(strategy_path)


def exception_retry_loop(harness, sentry, db):
    success = False
    backoff_seconds = BACKOFF_SECONDS_START

    while not success and not warm_shutdown_flag:
        success = handle_exception(harness, sentry)

        if not success:
            logger.info(tc.colored(
                'handle_exception failed, backing off for %s' % (
                humanize_seconds(backoff_seconds)),
                'red',
            ))

            gentle_sleep(backoff_seconds)
            backoff_seconds *= BACKOFF_MULTIPLIER
        else:
            logger.info(tc.colored(
                'handle_exception succeeded, full speed ahead',
                'green',
            ))

            return

        # This is necessary to flush local db cache and pick up changes other processes 
        # have made. For example, if this is a balance mismatch which was fixed by the
        # withdrawal tool.
        session.commit_mysql_session(db)


def handle_exception(harness, sentry):
    """
    Since much of our recovery code is in the audits, trying to handle an exception
    while we're not auditing is poorly defined. Possibly we should audit here so long
    as the strategy is running with db backing here, even if they are turned off in
    the configuration.
    """
    try:
        if harness.audit is True:
            harness.full_audit()

        return True
    except Exception as e:
        sentry.captureException()
        logger.exception(tc.colored(
            '[%s] %s' % (e.__class__.__name__, e.message),
            'red',
        ))

        return False


def live_run(configuration):
    strategy_name = configuration['platform']['strategy']
    is_builtin_strategy = configuration['platform']['builtin']
    execute = configuration['platform']['execute']
    backtest = configuration['platform']['backtest']
    backtest_file_path = configuration['backtest']['file_path']
    backtest_commission = float(configuration['backtest']['commission'])

    if execute == True and backtest == True:
        raise Exception("execute and backtest can not run simultaneously")
    
    if backtest == True:
        logger.info('live_run backtest(%s, %s)' % (strategy_name, backtest))
    else:
        logger.info('live_run execute(%s, %s)' % (strategy_name, execute))

    db = session.get_a_trading_db_mysql_session()

    harness = Harness(db, configuration)

    strategy_class = get_strategy_class(strategy_name, is_builtin_strategy)
    strategy = strategy_class(db, harness, configuration['strategy'], configuration['backtest'])
    strategy.set_up()

    harness.strategy = strategy

    if execute:
        EventRecorder().create(db=db)
        DatumRecorder().create(db=db)
    else:
        EventRecorder().create()
        DatumRecorder().create()

    sentry = Sentry(configuration['platform']['sentry'])
    heartbeat = Heartbeat(configuration['platform']['heartbeat'])
    

    if backtest == False :

        strategy.mode = 'execute'

        try:
            tick_count = 0

            while True:
                try:
                    tick_start = Delorean().epoch
                    print('\n\n%s' % strategy.name)

                    if warm_shutdown_flag:
                        return  # This takes us into the finally block.

                    # Initial audit. This is done inside the main loop so that our robust
                    # exception catching kicks in on initial audit failures.
                    if harness.audit is True and tick_count == 0:
                        # We try a fast audit (no wind down) since the bots usually start
                        # from a clean slate.
                        try:
                            harness.full_audit(wind_down=False)
                        except AuditException:
                            logger.info(
                                'Bot was not cleanly shut down, winding down and auditing',
                            )

                            harness.full_audit(wind_down=True)

                    # Regular audits.
                    if (harness.audit is True
                            and tick_count > 0
                            and tick_count % harness.audit_tick == 0):
                        harness.full_audit()
                    else:
                        harness.tick()

                        harness.post_tick(tick_count)

                    tick_profiling.record_tick_data(tick_start, strategy.name)
                    tick_profiling.record_tick_block_data(
                        strategy,
                        tick_count,
                        strategy.name,
                    )

                    heartbeat.heartbeat(strategy.name)

                except Exception as e:
                    sentry.captureException()

                    logger.exception(tc.colored(
                        '[%s] %s' % (e.__class__.__name__, e.message),
                        'red',
                    ))

                    exception_retry_loop(harness, sentry, db)
                finally:
                    session.commit_mysql_session(db)
                    tick_count += 1

                if harness.strategy_complete() is True:
                    break
                else:
                    gentle_sleep(harness.sleep_time_to_next_tick())
        finally:
            warm_shutdown(harness, db, sentry, execute)
            session.commit_mysql_session(db)
            db.remove()

            if restart_flag:
                restart()

    
    else:
        strategy.mode = 'backtest'

        # logger.info(tc.colored(' Backtesting engine is not implemented yet', 'red'))

        from execution.models.backtesting import backtrader_feed_extension as bt_ext
        bt_ext.run(
            gryphon_strategy_class=strategy, 
            data_path=backtest_file_path,
            commission=backtest_commission
            )