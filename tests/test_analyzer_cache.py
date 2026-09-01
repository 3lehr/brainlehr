from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kern.analyzer_cache import create, verify


def test_signed_cache_binds_tool_config_input_output_revision_and_version():
    key = Ed25519PrivateKey.generate()
    hashes = {name: (name[0] * 64) for name in ("tool", "config", "input", "output")}
    envelope = create(revision="r1", tool_sha256=hashes["tool"], config_sha256=hashes["config"],
                      input_sha256=hashes["input"], output_sha256=hashes["output"],
                      tool_version="1.0", actor="local", private_key=key)
    assert verify(envelope, revision="r1", tool_version="1.0", public_key=key.public_key())
    assert not verify(envelope, revision="r2", tool_version="1.0", public_key=key.public_key())
    assert not verify(envelope, revision="r1", tool_version="2.0", public_key=key.public_key())
    assert not verify({**envelope, "output_sha256": "x" * 64}, revision="r1", tool_version="1.0", public_key=key.public_key())
