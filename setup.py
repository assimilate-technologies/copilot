from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in copilot/__init__.py
from copilot import __version__ as version

setup(
	name="copilot",
	version=version,
	description="Your AI Powered Companion For Frappe Apps",
	author="Assimilate Technologies",
	author_email="developer@assimilatetechnologies.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
