"""Platform selection: audio backend and FreeRDP client (OpenBSD port)."""

from avd_feed_connect import config
from avd_feed_connect.rdp import launcher


def test_audio_defaults_to_pulse_off_openbsd(monkeypatch):
    monkeypatch.delenv("AVD_SOUND", raising=False)
    monkeypatch.setattr(config, "IS_OPENBSD", False)
    assert config.audio_args() == ["/sound:sys:pulse", "/microphone"]


def test_audio_uses_sndio_on_openbsd(monkeypatch):
    monkeypatch.delenv("AVD_SOUND", raising=False)
    monkeypatch.setattr(config, "IS_OPENBSD", True)
    assert config.audio_args() == ["/sound:sys:sndio", "/microphone:sys:sndio"]


def test_audio_env_override_and_none(monkeypatch):
    monkeypatch.setenv("AVD_SOUND", "oss")
    assert config.audio_args() == ["/sound:sys:oss", "/microphone:sys:oss"]
    monkeypatch.setenv("AVD_SOUND", "none")
    assert config.audio_args() == []


def test_falls_back_to_xfreerdp(monkeypatch, tmp_path):
    monkeypatch.delenv("AVD_SDL_FREERDP", raising=False)
    monkeypatch.setattr(config, "HOME", str(tmp_path))
    monkeypatch.setattr(config.shutil, "which",
                        lambda name: "/usr/local/bin/xfreerdp" if name == "xfreerdp" else None)
    assert config.find_sdl_freerdp() == "/usr/local/bin/xfreerdp"


def test_prefers_sdl_client_when_present(monkeypatch):
    monkeypatch.delenv("AVD_SDL_FREERDP", raising=False)
    monkeypatch.setattr(config.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert config.find_sdl_freerdp() == "/usr/bin/sdl-freerdp"


def test_env_override_wins(monkeypatch):
    monkeypatch.setenv("AVD_SDL_FREERDP", "/opt/x/xfreerdp")
    assert config.find_sdl_freerdp() == "/opt/x/xfreerdp"


def test_cli_argv_uses_sndio_on_openbsd(monkeypatch, tmp_path):
    monkeypatch.delenv("AVD_SOUND", raising=False)
    monkeypatch.setattr(config, "IS_OPENBSD", True)
    rdp = tmp_path / "r.rdp"
    rdp.write_text("enablerdsaadauth:i:1\n")
    argv = launcher.build_argv("/usr/local/bin/xfreerdp", str(rdp), "")
    assert "/sound:sys:sndio" in argv and "/microphone:sys:sndio" in argv
    assert not any("pulse" in a for a in argv)


def test_hotkeys_skipped_for_xfreerdp(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SDL", "/usr/local/bin/xfreerdp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert launcher.apply_client_hotkeys("on") is True
    assert not (tmp_path / "freerdp" / "sdl-freerdp.json").exists()
