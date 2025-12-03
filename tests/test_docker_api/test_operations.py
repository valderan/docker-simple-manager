"""Тесты функций docker_api (containers/images/volumes/builds)."""

from __future__ import annotations

from typing import Any

from src.connections.models import Connection
from src.docker_api.client import DockerClientWrapper
from src.docker_api import containers, images, volumes, builds


class FakeImage:
    def __init__(self) -> None:
        self.id = "sha256:123"
        self.tags = ["demo:latest"]
        self.attrs = {"Size": 1024}


class FakeContainer:
    def __init__(self) -> None:
        self.id = "abc"
        self.short_id = "abc"
        self.name = "demo"
        self.status = "running"
        self.image = FakeImage()
        self.attrs = {
            "NetworkSettings": {
                "Ports": {
                    "80/tcp": [
                        {
                            "HostIp": "0.0.0.0",
                            "HostPort": "8080",
                        }
                    ]
                }
            }
        }
        self.labels = {"com.docker.compose.project": "demo"}
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def stats(self, stream: bool = False) -> dict[str, Any]:
        return {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 200000000},
                "system_cpu_usage": 400000000,
                "online_cpus": 2,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 100000000},
                "system_cpu_usage": 200000000,
            },
            "memory_stats": {
                "usage": 50 * 1024 * 1024,
                "limit": 200 * 1024 * 1024,
            },
            "networks": {
                "eth0": {
                    "rx_bytes": 1024,
                    "tx_bytes": 2048,
                }
            },
            "blkio_stats": {
                "io_service_bytes_recursive": [
                    {"op": "Read", "value": 4096},
                    {"op": "Write", "value": 8192},
                ]
            },
            "pids_stats": {"current": 5},
        }


class FakeVolume:
    def __init__(self) -> None:
        self.name = "vol"
        self.attrs = {"Driver": "local", "Mountpoint": "/data"}
        self.removed = False

    def remove(self, force: bool = False) -> None:
        self.removed = force


class FakeRawClient:
    def __init__(self) -> None:
        self.container = FakeContainer()
        self.volume = FakeVolume()

        class Containers:
            def __init__(self, outer: FakeRawClient) -> None:
                self.outer = outer

            def list(self, all: bool = True) -> list[FakeContainer]:
                return [self.outer.container]

            def get(self, container_id: str) -> FakeContainer:
                return self.outer.container

        class Images:
            def list(self) -> list[FakeImage]:
                return [FakeImage()]

            def remove(self, image_id: str, force: bool = False) -> None:
                return None

        class Volumes:
            def __init__(self, outer: FakeRawClient) -> None:
                self.outer = outer

            def list(self) -> list[FakeVolume]:
                return [self.outer.volume]

            def get(self, name: str) -> FakeVolume:
                return self.outer.volume

        class API:
            def build_history(self) -> list[dict[str, Any]]:
                return [{"id": "build1", "tags": ["demo"], "created": 0}]

        self.containers = Containers(self)
        self.images = Images()
        self.volumes = Volumes(self)
        self.api = API()


def make_wrapper() -> DockerClientWrapper:
    connection = Connection(identifier="local", name="Local", socket="unix:///var/run/docker.sock")
    return DockerClientWrapper(connection, raw_client=FakeRawClient())


def test_containers_operations() -> None:
    wrapper = make_wrapper()
    results = containers.list_containers(wrapper)
    assert results[0]["name"] == "demo"
    containers.start_container(wrapper, "abc")
    containers.stop_container(wrapper, "abc")
    assert wrapper.get_raw_client().container.started
    assert wrapper.get_raw_client().container.stopped


def test_images_operations() -> None:
    wrapper = make_wrapper()
    results = images.list_images(wrapper)
    assert results[0]["tags"] == ["demo:latest"]
    images.remove_image(wrapper, "sha256:123", force=True)


def test_volumes_operations() -> None:
    wrapper = make_wrapper()
    results = volumes.list_volumes(wrapper)
    assert results[0]["name"] == "vol"
    volumes.remove_volume(wrapper, "vol", force=True)
    assert wrapper.get_raw_client().volume.removed is True


def test_builds_operations() -> None:
    wrapper = make_wrapper()
    results = builds.list_builds(wrapper)
    assert results[0]["id"] == "build1"
