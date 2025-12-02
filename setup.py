"""Setup script for softlight_automation_framework."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="softlight_automation_framework",
    version="1.0.0",
    author="Browser Automation Team",
    author_email="team@example.com",
    description="A multi-agent browser automation framework using OpenAI GPT and Playwright",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/softlight_automation_framework",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "browser-agent=softlight_automation_framework.cli.runner:main",
        ],
    },
)

