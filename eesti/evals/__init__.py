"""Evaluation harnesses.

Submodules are imported lazily and deliberately: `gec` needs only an HTTP client,
while `morphology` pulls in Vabamorf. Keeping them apart means the model eval can
run in CI on a bare Python image, with no compiled extensions to build.
"""
