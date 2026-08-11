"""Tests for gh-ops core — strict table parsing, formatting, CLI detection, argv building, error paths."""
import os
import subprocess
import sys
import unittest
from unittest import mock

# Make `import core` work no matter which directory discovery starts from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core

# Realistic `gh pr list` output (preamble, header, rows incl. a draft and a
# merged PR, plus a footer hint line that must be skipped).
PR_TABLE = """\
Showing 4 of 4 open pull requests in octocat/Hello-World

NUMBER  TITLE                          BRANCH          STATE  DRAFT
#14     Add the octocat logo           main            OPEN   false
#13     Update README with new info    main            OPEN   false
#12     Fix flaky tests on Windows CI  fix-ci          OPEN   true
#11     Bump deps                      dependabot/npm  MERGED false
Use `gh pr list --author @me` to list your own pull requests.
"""

ISSUE_TABLE = """\
NUMBER  TITLE                                        LABELS         STATE
#5      Crash when opening settings.json             bug,high       OPEN
#4      Document the /gh plugin                       documentation   OPEN
#3      Ship a v1.0.0 release                                             OPEN
#2      Drop support for Python 3.8                   breaking,tech  CLOSED
"""

# Real piped `gh` output (non-TTY): TAB-separated, no header line.
PR_TSV = (
    "14120\tchore(deps): bump github.com/klauspost/compress from 1.19.1 to 1.19.2\t"
    "dependabot/go_modules/github.com/klauspost/compress-1.19.2\tOPEN\t2026-08-10T14:03:49Z\n"
    "14108\tAllow public extension installs past SAML enforcement\t"
    "loganrosen:loganrosen-fix-extension-saml-install\tOPEN\t2026-08-08T22:01:01Z\n"
)

# Note the piped issue-list column order: number \t state \t title \t labels \t created
ISSUE_TSV = (
    "14118\tOPEN\t`gh skill` ignores `PI_CODING_AGENT_DIR` for Pi user-scope skills\t"
    "enhancement, gh-skill\t2026-08-10T09:58:55Z\n"
    "14093\tOPEN\t`gh stack submit` fails with `authentication token not found for host github.com`\t"
    "\t2026-08-07T23:20:27Z\n"
)

EMPTY_PRS = "No pull requests found"
EMPTY_PRS_OLD = "There are no open pull requests in octocat/Hello-World"
EMPTY_ISSUES = "No issues found"
EMPTY_ISSUES_OLD = "There are no open issues in octocat/Hello-World"


class ParsePrListTests(unittest.TestCase):
    def test_realistic_table(self):
        items = core.parse_pr_list(PR_TABLE)
        self.assertEqual(len(items), 4)
        first = items[0]
        self.assertEqual(first["number"], 14)
        self.assertEqual(first["title"], "Add the octocat logo")
        self.assertEqual(first["branch"], "main")
        self.assertEqual(first["state"], "OPEN")
        self.assertIs(first["draft"], False)
        # draft PR flagged
        self.assertIs(items[2]["draft"], True)
        self.assertEqual(items[2]["branch"], "fix-ci")
        # merged PR state preserved
        self.assertEqual(items[3]["state"], "MERGED")
        # footer hint line skipped, not parsed as an item
        self.assertNotIn(9999, [i["number"] for i in items])

    def test_title_with_spaces_is_not_split(self):
        items = core.parse_pr_list(PR_TABLE)
        self.assertEqual(items[1]["title"], "Update README with new info")

    def test_empty_variants(self):
        self.assertEqual(core.parse_pr_list(EMPTY_PRS), [])
        self.assertEqual(core.parse_pr_list(EMPTY_PRS_OLD), [])

    def test_empty_with_preamble(self):
        text = "Showing 0 of 0 open pull requests in octocat/Hello-World\n\nNo pull requests found"
        self.assertEqual(core.parse_pr_list(text), [])

    def test_garbage_no_header(self):
        self.assertEqual(core.parse_pr_list("not a gh table at all"), [])
        self.assertEqual(core.parse_pr_list(""), [])

    def test_multi_column_ragged_spacing(self):
        # Header with very different column widths; rows are padded to the
        # header positions (as gh always does). Titles keep their spaces.
        text = (
            "NUMBER      TITLE                    BRANCH        STATE   DRAFT\n"
            "#101        fix: null pointer        core          OPEN    false\n"
            "#100        add unit tests           tests         OPEN    true\n"
        )
        items = core.parse_pr_list(text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["number"], 101)
        self.assertEqual(items[0]["title"], "fix: null pointer")
        self.assertEqual(items[0]["branch"], "core")
        self.assertEqual(items[1]["branch"], "tests")
        self.assertIs(items[1]["draft"], True)

    def test_blank_line_between_rows_skipped(self):
        text = (
            "NUMBER  TITLE  BRANCH  STATE  DRAFT\n"
            "#1      A      main    OPEN   false\n"
            "\n"
            "#2      B      dev     OPEN   false\n"
        )
        self.assertEqual(len(core.parse_pr_list(text)), 2)

    def test_unknown_draft_value_is_not_draft(self):
        text = "NUMBER  TITLE  BRANCH  STATE  DRAFT\n#9      X      y       OPEN   n/a\n"
        items = core.parse_pr_list(text)
        self.assertIs(items[0]["draft"], False)

    def test_crlf_line_endings(self):
        items = core.parse_pr_list(PR_TABLE.replace("\n", "\r\n"))
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0]["title"], "Add the octocat logo")
        self.assertEqual(items[3]["state"], "MERGED")

    def test_header_only_no_rows(self):
        self.assertEqual(core.parse_pr_list("NUMBER  TITLE  BRANCH  STATE  DRAFT\n"), [])

    def test_none_input_is_empty(self):
        self.assertEqual(core.parse_pr_list(None), [])

    def test_missing_draft_column_does_not_crash(self):
        text = "NUMBER  TITLE  BRANCH  STATE\n#1      X      main    OPEN\n"
        items = core.parse_pr_list(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["number"], 1)
        self.assertEqual(items[0]["state"], "OPEN")
        self.assertIs(items[0]["draft"], False)  # absent column -> never invented

    def test_missing_branch_column_does_not_crash(self):
        text = "NUMBER  TITLE  STATE  DRAFT\n#1      X      OPEN   false\n"
        items = core.parse_pr_list(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["branch"], "")
        self.assertEqual(items[0]["state"], "OPEN")

    def test_missing_state_becomes_unknown(self):
        text = "NUMBER  TITLE  BRANCH  STATE  DRAFT\n#1      X      main\n"
        items = core.parse_pr_list(text)
        self.assertEqual(items[0]["state"], "UNKNOWN")

    def test_non_numeric_number_rows_skipped(self):
        text = (
            "NUMBER  TITLE  BRANCH  STATE  DRAFT\n"
            "#abc    broken row        OPEN   false\n"
            "N/A     another bad row   main   OPEN   true\n"
            "#2      good row          dev    OPEN   false\n"
        )
        items = core.parse_pr_list(text)
        self.assertEqual([i["number"] for i in items], [2])


class ParseIssueListTests(unittest.TestCase):
    def test_realistic_table(self):
        items = core.parse_issue_list(ISSUE_TABLE)
        self.assertEqual(len(items), 4)
        first = items[0]
        self.assertEqual(first["number"], 5)
        self.assertEqual(first["title"], "Crash when opening settings.json")
        self.assertEqual(first["labels"], "bug,high")
        self.assertEqual(first["state"], "OPEN")
        self.assertEqual(items[1]["labels"], "documentation")
        self.assertEqual(items[3]["state"], "CLOSED")

    def test_empty_variants(self):
        self.assertEqual(core.parse_issue_list(EMPTY_ISSUES), [])
        self.assertEqual(core.parse_issue_list(EMPTY_ISSUES_OLD), [])

    def test_empty_no_issues_wording(self):
        self.assertEqual(core.parse_issue_list("No issues are currently open"), [])

    def test_empty_labels_stays_empty_string(self):
        items = core.parse_issue_list(ISSUE_TABLE)
        self.assertEqual(items[2]["labels"], "")

    def test_garbage_no_header(self):
        self.assertEqual(core.parse_issue_list("random text"), [])

    def test_crlf_line_endings(self):
        items = core.parse_issue_list(ISSUE_TABLE.replace("\n", "\r\n"))
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0]["title"], "Crash when opening settings.json")

    def test_header_only_no_rows(self):
        self.assertEqual(core.parse_issue_list("NUMBER  TITLE  LABELS  STATE\n"), [])

    def test_missing_labels_column_does_not_crash(self):
        text = "NUMBER  TITLE  STATE\n#1      X      OPEN\n"
        items = core.parse_issue_list(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["labels"], "")
        self.assertEqual(items[0]["state"], "OPEN")

    def test_more_empty_wordings(self):
        for text in (
            "No results found",
            "No open issues are currently available",
            "There are no open issues",
            "NO PULL REQUESTS FOUND",
        ):
            with self.subTest(text=text):
                self.assertEqual(core.parse_issue_list(text), [])


class ParseTsvTests(unittest.TestCase):
    """Real piped (non-TTY) gh output: tab-separated rows, no header."""

    def test_pr_list_piped_tsv(self):
        items = core.parse_pr_list(PR_TSV)
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["number"], 14120)
        self.assertEqual(first["title"], "chore(deps): bump github.com/klauspost/compress from 1.19.1 to 1.19.2")
        self.assertEqual(first["branch"], "dependabot/go_modules/github.com/klauspost/compress-1.19.2")
        self.assertEqual(first["state"], "OPEN")
        self.assertIs(first["draft"], False)  # TSV has no draft column; never invented

    def test_issue_list_piped_tsv_column_order(self):
        items = core.parse_issue_list(ISSUE_TSV)
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["number"], 14118)
        self.assertEqual(first["state"], "OPEN")  # state precedes title in piped mode
        self.assertEqual(first["title"], "`gh skill` ignores `PI_CODING_AGENT_DIR` for Pi user-scope skills")
        self.assertEqual(first["labels"], "enhancement, gh-skill")

    def test_issue_list_piped_tsv_empty_labels(self):
        items = core.parse_issue_list(ISSUE_TSV)
        self.assertEqual(items[1]["labels"], "")

    def test_tsv_empty_message(self):
        self.assertEqual(core.parse_pr_list(EMPTY_PRS), [])
        self.assertEqual(core.parse_issue_list("No issues found"), [])

    def test_tsv_extra_columns_ignored(self):
        # A future gh adding a column must not corrupt the mapped fields.
        line = "7\tFix the thing\tmain\tOPEN\t2026-01-01T00:00:00Z\tEXTRA\n"
        items = core.parse_pr_list(line)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Fix the thing")
        self.assertEqual(items[0]["state"], "OPEN")

    def test_tsv_crlf_line_endings(self):
        items = core.parse_pr_list(PR_TSV.replace("\n", "\r\n"))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["number"], 14120)

    def test_tsv_short_row_pads_missing_cells(self):
        line = "5\tTitle only\n"
        items = core.parse_pr_list(line)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["number"], 5)
        self.assertEqual(items[0]["title"], "Title only")
        self.assertEqual(items[0]["branch"], "")
        self.assertEqual(items[0]["state"], "UNKNOWN")

    def test_tsv_footer_hint_skipped(self):
        text = PR_TSV + "Use `gh pr list --author @me` to list your own pull requests.\n"
        items = core.parse_pr_list(text)
        self.assertEqual(len(items), 2)

    def test_tsv_blank_lines_ignored(self):
        text = "7\tFix the thing\tmain\tOPEN\t2026-01-01T00:00:00Z\n\n\n"
        items = core.parse_pr_list(text)
        self.assertEqual(len(items), 1)

    def test_issue_tsv_extra_columns_ignored(self):
        line = "9\tOPEN\tTitle here\tbug\t2026-01-01T00:00:00Z\tEXTRA\n"
        items = core.parse_issue_list(line)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Title here")
        self.assertEqual(items[0]["labels"], "bug")


class FormatSummaryTests(unittest.TestCase):
    def test_pr_shape(self):
        items = core.parse_pr_list(PR_TABLE)
        out = core.format_summary(items, "pr")
        lines = out.splitlines()
        self.assertEqual(lines[0], "4 PRs:")
        self.assertTrue(lines[1].startswith("  #14 Add the octocat logo [OPEN] branch: main"))
        self.assertIn("[OPEN, draft] branch: fix-ci", out)
        self.assertIn("[MERGED] branch: dependabot/npm", out)

    def test_issue_shape(self):
        items = core.parse_issue_list(ISSUE_TABLE)
        out = core.format_summary(items, "issue")
        lines = out.splitlines()
        self.assertEqual(lines[0], "4 issues:")
        self.assertTrue(lines[1].startswith("  #5 Crash when opening settings.json [OPEN]"))
        self.assertIn("labels: bug,high", out)
        self.assertNotIn("labels:  ", out)  # empty labels produce no suffix

    def test_empty(self):
        self.assertEqual(core.format_summary([], "pr"), "No pull requests found.")
        self.assertEqual(core.format_summary([], "issue"), "No issues found.")

    def test_singular(self):
        items = [{"number": 1, "title": "Only one", "branch": "main", "state": "OPEN", "draft": False}]
        out = core.format_summary(items, "pr")
        self.assertEqual(out.splitlines()[0], "1 PR:")
        self.assertEqual(out.splitlines()[1], "  #1 Only one [OPEN] branch: main")

    def test_unknown_kind_empty(self):
        self.assertEqual(core.format_summary([], "banana"), "Nothing found.")
        self.assertEqual(core.format_summary([], None), "Nothing found.")

    def test_unknown_kind_nonempty(self):
        items = [{"number": 1, "title": "T", "state": "OPEN"}]
        out = core.format_summary(items, "banana")
        self.assertEqual(out.splitlines()[0], "1 item:")
        self.assertIn("#1 T [OPEN]", out)

    def test_issue_singular(self):
        items = [{"number": 7, "title": "Only", "labels": "", "state": "OPEN"}]
        out = core.format_summary(items, "issue")
        self.assertEqual(out.splitlines()[0], "1 issue:")

    def test_pr_missing_branch_renders_dash(self):
        items = [{"number": 3, "title": "No branch", "state": "OPEN", "draft": False}]
        out = core.format_summary(items, "pr")
        self.assertIn("branch: -", out)

    def test_issue_empty_labels_no_suffix(self):
        items = [{"number": 4, "title": "Bare", "labels": "", "state": "OPEN"}]
        out = core.format_summary(items, "issue")
        self.assertNotIn("labels:", out)


class DetectCliTests(unittest.TestCase):
    def test_both_installed(self):
        with mock.patch.object(core.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"):
            self.assertEqual(core.detect_cli(), {"gh": True, "glab": True})

    def test_none_installed(self):
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertEqual(core.detect_cli(), {"gh": False, "glab": False})

    def test_gh_only(self):
        def which(name):
            return "/x/gh" if name == "gh" else None
        with mock.patch.object(core.shutil, "which", side_effect=which):
            self.assertEqual(core.detect_cli(), {"gh": True, "glab": False})


class GhArgvTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(core.gh_argv("status"), ["gh", "auth", "status"])

    def test_me(self):
        self.assertEqual(core.gh_argv("me"), ["gh", "api", "user", "--jq", ".login"])

    def test_prs_default(self):
        self.assertEqual(core.gh_argv("prs"), ["gh", "pr", "list", "--limit", "20"])

    def test_prs_with_repo(self):
        self.assertEqual(
            core.gh_argv("prs", "octocat/Hello-World"),
            ["gh", "pr", "list", "--limit", "20", "--repo", "octocat/Hello-World"],
        )

    def test_issues_default(self):
        self.assertEqual(core.gh_argv("issues"), ["gh", "issue", "list", "--limit", "20"])

    def test_issues_with_repo(self):
        self.assertEqual(
            core.gh_argv("issues", "cli/cli"),
            ["gh", "issue", "list", "--limit", "20", "--repo", "cli/cli"],
        )

    def test_case_insensitive_and_whitespace(self):
        self.assertEqual(core.gh_argv("  PRS ", "  cli/cli "), ["gh", "pr", "list", "--limit", "20", "--repo", "cli/cli"])

    def test_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            core.gh_argv("frobnicate")

    def test_prs_empty_repo_omits_flag(self):
        for repo in ("", "   ", None):
            self.assertEqual(core.gh_argv("prs", repo), ["gh", "pr", "list", "--limit", "20"])

    def test_issues_empty_repo_omits_flag(self):
        for repo in ("", "   ", None):
            self.assertEqual(core.gh_argv("issues", repo), ["gh", "issue", "list", "--limit", "20"])

    def test_status_and_me_ignore_repo(self):
        self.assertEqual(core.gh_argv("status", "octocat/x"), ["gh", "auth", "status"])
        self.assertEqual(core.gh_argv("me", "octocat/x"), ["gh", "api", "user", "--jq", ".login"])

    def test_none_or_empty_action_raises(self):
        with self.assertRaises(ValueError):
            core.gh_argv(None)
        with self.assertRaises(ValueError):
            core.gh_argv("")


class ClassifyErrorTests(unittest.TestCase):
    """classify_error: auth vs network vs generic error strings."""

    def test_auth_variants(self):
        for err in (
            "You are not logged in to any GitHub hosts.",
            "gh: To use 'gh pr', please run 'gh auth login' first.",
            "authentication required",
            "Please log in via 'gh auth login'.",
        ):
            with self.subTest(err=err):
                self.assertIn("not authenticated", core.classify_error(err, 1))

    def test_network_variants(self):
        for err in (
            "dial tcp: lookup api.github.com: no such host",
            "Get https://api.github.com: dial tcp: connection refused",
            "connection reset by peer",
            "request timed out after 30s",
            "net/http: TLS handshake timeout",
            "connect: network is unreachable",
            "failed to connect to api.github.com port 443",
            "github.com:443: http 500: Internal Server Error",
        ):
            with self.subTest(err=err):
                self.assertIn("network error", core.classify_error(err, 1))

    def test_network_error_takes_first_line(self):
        msg = core.classify_error(
            "dial tcp: lookup api.github.com: no such host\nmore detail", 1
        )
        self.assertEqual(
            msg, "network error talking to GitHub: dial tcp: lookup api.github.com: no such host"
        )

    def test_auth_checked_before_network(self):
        self.assertIn("not authenticated", core.classify_error("not logged in — connection refused", 1))

    def test_whitespace_stderr_falls_back_to_exit_code(self):
        self.assertEqual(core.classify_error("   \n\t", 7), "gh command failed (exit code 7).")

    def test_generic_takes_first_line(self):
        self.assertEqual(core.classify_error("boom\nsecond line", 2), "gh error: boom")

    def test_none_stderr_falls_back(self):
        self.assertEqual(core.classify_error(None, 3), "gh command failed (exit code 3).")


class RunGhTests(unittest.TestCase):
    def _fake(self, returncode=0, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_success(self):
        fake = self._fake(stdout="hello")
        with mock.patch.object(core.subprocess, "run", return_value=fake) as m:
            res = core.run_gh(["gh", "pr", "list"])
        self.assertTrue(res["ok"])
        self.assertEqual(res["stdout"], "hello")
        self.assertIsNone(res["error"])
        m.assert_called_once_with(
            ["gh", "pr", "list"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30.0,
        )

    def test_cli_not_installed(self):
        with mock.patch.object(core.subprocess, "run", side_effect=FileNotFoundError):
            res = core.run_gh(["gh", "x"])
        self.assertFalse(res["ok"])
        self.assertIn("not installed", res["error"])

    def test_timeout(self):
        with mock.patch.object(core.subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=30)):
            res = core.run_gh(["gh", "x"])
        self.assertFalse(res["ok"])
        self.assertIn("timed out", res["error"])

    def test_auth_error_classified(self):
        fake = self._fake(returncode=1, stderr="gh: To use 'gh pr', please run 'gh auth login' first.")
        with mock.patch.object(core.subprocess, "run", return_value=fake):
            res = core.run_gh(["gh", "pr", "list"])
        self.assertFalse(res["ok"])
        self.assertIn("not authenticated", res["error"])

    def test_network_error_classified(self):
        fake = self._fake(returncode=1, stderr="dial tcp: lookup api.github.com: no such host")
        with mock.patch.object(core.subprocess, "run", return_value=fake):
            res = core.run_gh(["gh", "pr", "list"])
        self.assertFalse(res["ok"])
        self.assertIn("network error", res["error"])

    def test_generic_error_takes_first_line(self):
        fake = self._fake(returncode=2, stderr="boom happened\nmore detail")
        with mock.patch.object(core.subprocess, "run", return_value=fake):
            res = core.run_gh(["gh", "x"])
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "gh error: boom happened")

    def test_empty_stderr_falls_back_to_exit_code(self):
        fake = self._fake(returncode=3, stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake):
            res = core.run_gh(["gh", "x"])
        self.assertEqual(res["error"], "gh command failed (exit code 3).")

    def test_whitespace_stderr_falls_back(self):
        fake = self._fake(returncode=4, stderr="   ")
        with mock.patch.object(core.subprocess, "run", return_value=fake):
            res = core.run_gh(["gh", "x"])
        self.assertEqual(res["error"], "gh command failed (exit code 4).")

    def test_timeout_message_includes_seconds(self):
        with mock.patch.object(
            core.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=15),
        ):
            res = core.run_gh(["gh", "x"], timeout=15)
        self.assertEqual(res["error"], "gh command timed out after 15s.")

    def test_success_empty_stdout_ok(self):
        fake = self._fake(returncode=0, stdout="")
        with mock.patch.object(core.subprocess, "run", return_value=fake):
            res = core.run_gh(["gh", "x"])
        self.assertTrue(res["ok"])
        self.assertEqual(res["stdout"], "")
        self.assertIsNone(res["error"])


class ExecuteTests(unittest.TestCase):
    """Handler routing: correct argv reaches subprocess; output is parsed+formatted."""

    def test_prs_full_chain_with_mocked_subprocess(self):
        fake = mock.Mock(returncode=0, stdout=PR_TABLE, stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake) as m, \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("prs", "octocat/Hello-World")
        m.assert_called_once_with(
            ["gh", "pr", "list", "--limit", "20", "--repo", "octocat/Hello-World"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30.0,
        )
        self.assertIn("4 PRs:", out)
        self.assertIn("#12 Fix flaky tests on Windows CI [OPEN, draft] branch: fix-ci", out)

    def test_prs_full_chain_piped_tsv(self):
        # What real `gh pr list` emits when captured (no header, tabs).
        fake = mock.Mock(returncode=0, stdout=PR_TSV, stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake) as m, \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("prs")
        m.assert_called_once_with(
            ["gh", "pr", "list", "--limit", "20"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30.0,
        )
        self.assertIn("2 PRs:", out)
        self.assertIn(
            "#14108 Allow public extension installs past SAML enforcement [OPEN] "
            "branch: loganrosen:loganrosen-fix-extension-saml-install",
            out,
        )

    def test_issues_full_chain(self):
        fake = mock.Mock(returncode=0, stdout=ISSUE_TABLE, stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake) as m, \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("issues")
        m.assert_called_once_with(
            ["gh", "issue", "list", "--limit", "20"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30.0,
        )
        self.assertIn("4 issues:", out)
        self.assertIn("labels: bug,high", out)

    def test_me(self):
        fake = mock.Mock(returncode=0, stdout="painbaba\n", stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake) as m, \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("me")
        m.assert_called_once_with(["gh", "api", "user", "--jq", ".login"], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=30.0)
        self.assertEqual(out, "Authenticated as painbaba")

    def test_status(self):
        fake = mock.Mock(returncode=0, stdout="github.com\n  ✓ Logged in to github.com account painbaba", stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake) as m, \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("status")
        m.assert_called_once_with(["gh", "auth", "status"], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=30.0)
        self.assertIn("gh: installed | glab: NOT installed", out)
        self.assertIn("Logged in to github.com account painbaba", out)

    def test_empty_prs_formatted(self):
        fake = mock.Mock(returncode=0, stdout=EMPTY_PRS, stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake), \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("prs")
        self.assertEqual(out, "No pull requests found.")

    def test_gh_missing_message(self):
        with mock.patch.object(core, "detect_cli", return_value={"gh": False, "glab": False}), \
             mock.patch.object(core.subprocess, "run") as m:
            out = core.execute("prs")
        m.assert_not_called()
        self.assertIn("gh CLI not installed", out)
        self.assertIn("glab CLI not installed", out)

    def test_gh_missing_glab_present_message(self):
        with mock.patch.object(core, "detect_cli", return_value={"gh": False, "glab": True}), \
             mock.patch.object(core.subprocess, "run") as m:
            out = core.execute("me")
        m.assert_not_called()
        self.assertIn("gh CLI not installed", out)
        self.assertNotIn("glab CLI not installed", out)

    def test_unknown_action(self):
        self.assertIn("Unknown gh_ops action", core.execute("frobnicate"))

    def test_error_propagates_cleanly(self):
        with mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}), \
             mock.patch.object(core, "run_gh", return_value={
                 "ok": False, "stdout": "", "stderr": "gh: please run 'gh auth login' first.",
                 "error": "gh is not authenticated — run 'gh auth login' first.",
             }):
            out = core.execute("prs")
        self.assertEqual(out, "gh is not authenticated — run 'gh auth login' first.")

    def test_prs_empty_repo_argv(self):
        for repo in (None, "", "  "):
            fake = mock.Mock(returncode=0, stdout=EMPTY_PRS, stderr="")
            with mock.patch.object(core.subprocess, "run", return_value=fake) as m, \
                 mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
                core.execute("prs", repo)
            m.assert_called_once_with(
                ["gh", "pr", "list", "--limit", "20"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30.0,
            )

    def test_me_empty_stdout(self):
        fake = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=fake), \
             mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}):
            out = core.execute("me")
        self.assertEqual(out, "Authenticated (login unavailable)")

    def test_execute_none_action(self):
        self.assertIn("Unknown gh_ops action", core.execute(None))

    def test_network_error_propagates(self):
        with mock.patch.object(core, "detect_cli", return_value={"gh": True, "glab": False}), \
             mock.patch.object(core, "run_gh", return_value={
                 "ok": False, "stdout": "", "stderr": "dial tcp: no such host",
                 "error": "network error talking to GitHub: dial tcp: no such host",
             }):
            out = core.execute("prs")
        self.assertIn("network error", out)


if __name__ == "__main__":
    unittest.main()
