from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='lessllm',
    version='0.1.0',
    author='simpx',
    author_email='simpxx@gmail.com',
    description='A lightweight LLM API proxy framework with network connectivity and usage analysis',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/simpx/lessllm',
    packages=find_packages(),
    install_requires=[
        'fastapi>=0.104.0',
        'uvicorn[standard]>=0.24.0',
        'httpx>=0.25.0',
        'pydantic>=2.0.0',
        'pyyaml>=6.0',
        'duckdb>=0.9.0',
        'python-multipart>=0.0.6',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'flake8>=6.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'lessllm=lessllm.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: Proxy Servers',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
    keywords='llm, api, proxy, openai, claude, anthropic, analysis, performance, cache',
)
