"""Windows rule pack tests for sandbox-gate.

Covers the PowerShell/cmd destructive-verb block families (Remove-Item
-Recurse, Clear-Content, Format-Volume/Partition, diskpart, reg delete,
Set-ExecutionPolicy, cmd del /s, cmd rd /s, wmic delete, schtasks /delete,
sc stop/delete), the package-install warn families (choco install -y,
npm i -g, pip install --user), case-insensitivity, and the benign
PowerShell Get-*/query/display commands that must stay allowed.

Pure string classification — no command is ever executed.
"""
import importlib.util
import os
import unittest

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_core():
    spec = importlib.util.spec_from_file_location(
        "sandbox_gate_core",
        os.path.join(PLUGIN_DIR, "core.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


core = _load_core()


class WindowsBlockRuleTestCase(unittest.TestCase):
    """Windows destructive verbs must return ('block', reason)."""

    def test_block_powershell_remove_item_recurse(self):
        cases = [
            'powershell -Command "Remove-Item -Recurse C:\\Temp"',
            'powershell.exe -Command "Remove-Item -Recurse -Force C:\\Windows\\System32"',
            "Remove-Item -Path D:\\old -Recurse",
            'powershell -Command "Get-ChildItem | Remove-Item -Recurse C:\\Temp"',
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                verdict, reason = core.classify(cmd)
                self.assertEqual(verdict, core.VERDICT_BLOCK, cmd)
                self.assertIn("Remove-Item", reason)

    def test_block_powershell_clear_content_and_disk_format(self):
        cases = [
            'powershell -Command "Clear-Content C:\\logs\\app.log"',
            'powershell -Command "Format-Volume -DriveLetter D"',
            'powershell -Command "Format-Partition -DiskNumber 1"',
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(core.classify(cmd)[0], core.VERDICT_BLOCK, cmd)

    def test_block_diskpart_reg_delete_set_execution_policy(self):
        cases = [
            "diskpart /s wipe.txt",
            "diskpart.exe /s clean.txt",
            "reg delete HKLM\\Software\\Vendor /f",
            'powershell -Command "Set-ExecutionPolicy Unrestricted"',
            'powershell -Command "Set-ExecutionPolicy -Scope CurrentUser Bypass"',
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(core.classify(cmd)[0], core.VERDICT_BLOCK, cmd)

    def test_block_cmd_recursive_delete(self):
        cases = [
            "cmd /c del /s /q C:\\*",
            "cmd /c rd /s /q C:\\Windows",
            "cmd /c rmdir /s /q D:\\old",
            "del /s /q C:\\temp\\*",
            "rd /s /q C:\\temp",
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(core.classify(cmd)[0], core.VERDICT_BLOCK, cmd)

    def test_block_wmic_schtasks_sc(self):
        cases = [
            'wmic process where "name=\'x.exe\'" delete',
            "schtasks /delete /tn \"MyTask\" /f",
            "sc stop spooler",
            "sc delete MyService",
            "sc.exe stop wuauserv",
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(core.classify(cmd)[0], core.VERDICT_BLOCK, cmd)


class WindowsWarnRuleTestCase(unittest.TestCase):
    """Package installs must return ('warn', reason)."""

    def test_warn_package_installs(self):
        cases = [
            "choco install -y firefox",
            "choco install --yes git",
            "npm i -g eslint",
            "npm install --global typescript",
            "pip install --user requests",
            "pip3 install --user flask",
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                verdict, reason = core.classify(cmd)
                self.assertEqual(verdict, core.VERDICT_WARN, cmd)
                self.assertTrue(reason)


class WindowsCaseInsensitivityTestCase(unittest.TestCase):
    """All Windows patterns must match case-insensitively."""

    def test_windows_rules_case_insensitive(self):
        cases = [
            ('POWERSHELL -COMMAND "REMOVE-ITEM -RECURSE C:\\TEMP"', core.VERDICT_BLOCK),
            ("CMD /C DEL /S /Q C:\\*", core.VERDICT_BLOCK),
            ("CMD /C RD /S /Q C:\\WINDOWS", core.VERDICT_BLOCK),
            ('WMIC PROCESS WHERE NAME="X" DELETE', core.VERDICT_BLOCK),
            ('SCHTASKS /DELETE /TN "T" /F', core.VERDICT_BLOCK),
            ("SC STOP SPOOLER", core.VERDICT_BLOCK),
            ("REG DELETE HKLM\\SOFTWARE\\X /F", core.VERDICT_BLOCK),
            ("DISKPART /S WIPE.TXT", core.VERDICT_BLOCK),
            ("CHOCO INSTALL -Y FIREFOX", core.VERDICT_WARN),
            ("NPM I -G ESLINT", core.VERDICT_WARN),
            ("PIP INSTALL --USER REQUESTS", core.VERDICT_WARN),
        ]
        for cmd, expected in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(core.classify(cmd)[0], expected, cmd)


class WindowsAllowTestCase(unittest.TestCase):
    """Benign PowerShell Get-*/query/display commands must stay allowed."""

    def test_benign_powershell_get_and_queries_allowed(self):
        cases = [
            'powershell -Command "Get-ChildItem C:\\"',
            'powershell -Command "Get-Process"',
            'powershell -Command "Get-ExecutionPolicy"',
            'powershell -Command "Get-Service | Format-Table"',
            "Get-Content C:\\logs\\app.log",          # read, not Clear-Content
            "Get-Item C:\\x",                          # read, not Remove-Item
            "npm test",                                # no -g
            "npm i lodash",                            # local, not global
            "pip install requests",                    # no --user
            "sc query spooler",                        # query, not stop/delete
            "reg query HKLM\\Software",                # query, not delete
            "schtasks /query",                         # query, not /delete
            "wmic process get name",                   # get, not delete
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(core.classify(cmd)[0], core.VERDICT_ALLOW, cmd)
        # Structural check: the packs exist and are wired into the active
        # rule lists the classifier iterates.
        self.assertTrue(core.WINDOWS_BLOCK_RULES)
        self.assertTrue(core.WINDOWS_WARN_RULES)
        self.assertTrue(
            all(rule in core.BLOCK_RULES for rule in core.WINDOWS_BLOCK_RULES)
        )
        self.assertTrue(
            all(rule in core.WARN_RULES for rule in core.WINDOWS_WARN_RULES)
        )


if __name__ == "__main__":
    unittest.main()
