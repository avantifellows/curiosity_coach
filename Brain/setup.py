from setuptools import setup, find_packages

setup(
    name="brain",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai",
        "groq",
        "python-dotenv",
    ],
    python_requires=">=3.8",
) 