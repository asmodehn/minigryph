import os
import setuptools



class CleanCommand(setuptools.Command):
    """
    Custom clean command to tidy up the project root, because even
        python setup.py clean --all
    doesn't remove build/dist and egg-info directories, which can and have caused
    install problems in the past.
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')


with open('requirements.txt') as r:
    requirements = r.read().splitlines()


setuptools.setup(
    name='minigryph',
    packages=setuptools.find_packages(),
    version='0.1',
    description='A framework for running algorithmic trading strategies on cryptocurrency markets.',
    classifiers=(
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'License :: Other/Proprietary License',
    ),
    entry_points={
        'console_scripts': [
            'minigryph-runtests=gryphon.tests.runtests:main',
            'minigryph-exec=gryphon.execution.app:main',
            'minigryph-cli=gryphon.execution.console:main',
            'minigryph-dashboards=gryphon.dashboards.app:main',
        ],
    },
    include_package_data=True,
    install_requires=requirements,
    cmdclass={
        'clean': CleanCommand,
    },
)
