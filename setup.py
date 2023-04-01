from setuptools import setup, find_packages
setup(
    version="1.0",
    name="any_subtitle",
    packages=find_packages(),
    py_modules=["any_subtitle"],
    author="TianhaoZhang",
    install_requires=[
        'openai-whisper',
    ],
    description="Make your videos accessible to a wider audience by adding subtitles in your target language, with support for any language vedio.",
    entry_points={
        'console_scripts': ['any_subtitle=src.cli:main'],
    },
    include_package_data=True,
)
