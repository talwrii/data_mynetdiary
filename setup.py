import setuptools

setuptools.setup(
    name='foodcli',
    version=0.1,
    author='Tal Wrii',
    author_email='talwrii@gmail.com',
    description='',
    license='GPLv3',
    keywords='',
    url='',
    packages=[],
    long_description=open('README.md').read(),
    entry_points={
        'console_scripts': ['foodcli=foodcli.foodcli:main']

    },
    classifiers=[
    ],
    test_suite='nose.collector'
)
