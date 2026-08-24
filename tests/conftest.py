"""Skip the training suite when its optional extras are absent."""

collect_ignore_glob = []

try:  # torch is an optional training extra, not a publisher dependency
    import torch  # noqa: F401
except ModuleNotFoundError:
    collect_ignore_glob.append("test_training_*.py")
