# Houdin-io tests

The tests run the real actions against a mocked `app.houdin.io` (`tests/mock_session.py`): `POST /scan/launch` hands out scan IDs, `GET` and `POST /scan/result` answer `202` until the test calls `finish()`, and the documents returned are the example in `resources/scan_artifact_JsonResult_example.json`, re-addressed to the artifact. Nothing reaches the network.

```bash
# from the repository root
mp test --integration houdin_io
```

- `test_actions/`: Ping, Scan Artifact and Enrich Entities, including the asynchronous continuation (the `additional_data` handed back between runs).
- `test_core/`: the verdict extraction, enrichment fields and parameter parsing.
- `test_defaults/`: every module imports.
