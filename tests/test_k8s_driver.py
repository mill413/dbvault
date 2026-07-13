import subprocess

from app.drivers.database.k8s import K8sConfig, run_kubectl_command


def test_run_kubectl_command_resolves_label_selector_before_exec(monkeypatch):
    calls = []
    kwargs_seen = []

    def fake_run(args, **kwargs):
        calls.append(args)
        kwargs_seen.append(kwargs)
        if "get" in args:
            return subprocess.CompletedProcess(args, 0, stdout=b"mysql-0", stderr=b"")
        return subprocess.CompletedProcess(
            args,
            1,
            stdout=b"",
            stderr=b"MYSQL_PWD=secret failed",
        )

    monkeypatch.setattr("app.drivers.database.k8s.subprocess.run", fake_run)

    result = run_kubectl_command(
        K8sConfig(namespace="db", label_selector="app=mysql", container="mysql"),
        ["mysql", "-e", "SELECT VERSION();"],
        env={"MYSQL_PWD": "secret"},
    )

    assert result.ok is False
    assert result.stderr_tail == "MYSQL_PWD=*** failed"
    assert calls[0] == [
        "kubectl",
        "-n",
        "db",
        "get",
        "pods",
        "-l",
        "app=mysql",
        "-o",
        "jsonpath={.items[0].metadata.name}",
    ]
    assert calls[1][:5] == ["kubectl", "-n", "db", "exec", "mysql-0"]
    assert "-l" not in calls[1]
    separator_index = calls[1].index("--")
    assert calls[1][separator_index + 1 : separator_index + 3] == ["env", "MYSQL_PWD=secret"]
    assert kwargs_seen[1]["env"]["MYSQL_PWD"] == "secret"
    assert all("/tmp/dbvault-env-" not in " ".join(call) for call in calls)
    assert all("cat" not in call and "rm" not in call for call in calls)


def test_run_kubectl_command_reports_missing_pod(monkeypatch):
    monkeypatch.setattr(
        "app.drivers.database.k8s.subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b""),
    )

    result = run_kubectl_command(
        K8sConfig(namespace="db", label_selector="app=missing"),
        ["mysql", "-e", "SELECT VERSION();"],
    )

    assert result.ok is False
    assert result.returncode == 1
    assert "Kubernetes pod not found" in result.stderr_tail
