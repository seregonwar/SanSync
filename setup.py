from setuptools import setup
import sys

if sys.platform == 'win32':
	from cx_Freeze import setup, Executable
	
	base = 'Win32GUI'
	
	executables = [
		Executable(
			'main.py',
			base=base,
			target_name='SanSync.exe',
			icon='resources/icon.ico',
			manifest='SanSync.exe.manifest'
		)
	]
	
	build_options = {
		'packages': ['PyQt6'],
		'excludes': [],
		'include_files': [
			'scripts/',
			'.env.template',
			'README.md'
		]
	}
	
	setup(
		name='SanSync',
		version='1.0',
		description='GTA5 Co-op Mod',
		options={'build_exe': build_options},
		executables=executables
	)
else:
	setup(
		name='SanSync',
		version='1.0',
		description='GTA5 Co-op Mod',
		author='SanSync Team',
		packages=['client', 'server', 'scripts']
	)