import json
import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO_ROOT = Path(__file__).resolve().parent.parent


class UptimeKumaConfigTests(unittest.TestCase):
    def test_dockerfile_base_and_defaults(self):
        dockerfile_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertRegex(
            dockerfile_text,
            r"^FROM\s+ghcr\.io/louislam/uptime-kuma:2-slim\b",
        )
        self.assertIn("TZ=Asia/Taipei", dockerfile_text)
        self.assertIn("--max-old-space-size=192", dockerfile_text)
        self.assertIn("EXPOSE 3001", dockerfile_text)
        self.assertIn("CMD extra/healthcheck", dockerfile_text)

    def test_dockerignore_excludes_runtime_and_repo_files(self):
        ignore_lines = {
            line.strip()
            for line in (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        for required in [".git", ".github", ".env", "data", "tests", "docker-compose.yml", "synology-docker-config.json"]:
            self.assertIn(required, ignore_lines)

    def test_synology_docker_config_json(self):
        synology_path = REPO_ROOT / "synology-docker-config.json"
        data = json.loads(synology_path.read_text(encoding="utf-8"))
        self.assertEqual(data["image"], "ghcr.io/johntsai0320/uptime-kuma:latest")
        self.assertEqual(data["name"], "uptime-kuma")
        self.assertEqual(data["network_mode"], "bridge")
        self.assertFalse(data["use_host_network"])
        self.assertEqual(
            [(p["container_port"], p["host_port"], p["type"]) for p in data["port_bindings"]],
            [(3001, 3001, "tcp")],
        )
        self.assertEqual(
            [(v["host_volume_file"], v["mount_point"], v["type"]) for v in data["volume_bindings"]],
            [("/docker/uptime-kuma/data", "/app/data", "rw")],
        )
        env_map = {item["key"]: item["value"] for item in data["env_variables"]}
        self.assertEqual(env_map["TZ"], "Asia/Taipei")
        self.assertEqual(env_map["NODE_OPTIONS"], "--max-old-space-size=192")

    def test_compose_env_example_and_workflow_consistency(self):
        compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        env_text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        compose_vars = set(re.findall(r"\$\{([A-Z0-9_]+):-", compose_text))
        env_vars = set(re.findall(r"^#?\s*([A-Z0-9_]+)=", env_text, re.MULTILINE))
        self.assertEqual(compose_vars - env_vars, set(), f"Missing vars in .env.example: {compose_vars - env_vars}")

        synology_data = json.loads((REPO_ROOT / "synology-docker-config.json").read_text(encoding="utf-8"))
        synology_env_keys = {item["key"] for item in synology_data["env_variables"]}

        if yaml is not None:
            compose = yaml.safe_load(compose_text)
            svc = compose["services"]["uptime-kuma"]
            self.assertEqual(svc["build"], ".")
            self.assertEqual(svc["image"], "${UPTIME_KUMA_IMAGE:-ghcr.io/johntsai0320/uptime-kuma:latest}")
            self.assertEqual(svc["container_name"], "uptime-kuma")
            self.assertEqual(svc["mem_limit"], "256m")
            self.assertEqual(svc["memswap_limit"], "384m")
            self.assertEqual(svc["cpu_shares"], 512)
            self.assertIn("./data:/app/data", svc["volumes"])
            self.assertIn("host.docker.internal:host-gateway", svc["extra_hosts"])
            self.assertEqual(svc["healthcheck"]["test"], ["CMD", "extra/healthcheck"])

            compose_env_keys = {item.split("=", 1)[0] for item in svc["environment"]}
            self.assertEqual(synology_env_keys, compose_env_keys)

            workflow = yaml.safe_load(
                (REPO_ROOT / ".github" / "workflows" / "docker-publish.yml").read_text(encoding="utf-8")
            )
            self.assertIn("verify", workflow["jobs"])
            self.assertIn("build", workflow["jobs"])
            self.assertIn("merge", workflow["jobs"])
            self.assertEqual(
                workflow["jobs"]["build"]["strategy"]["matrix"]["platform"],
                ["linux/amd64", "linux/arm64"],
            )


if __name__ == "__main__":
    unittest.main()
