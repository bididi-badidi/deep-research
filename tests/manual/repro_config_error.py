import os
from config import Config


def test_config_invalid_env_var():
    os.environ["MAX_TOKENS"] = "not-an-int"
    print("Attempting to instantiate Config with MAX_TOKENS=not-an-int")
    try:
        cfg = Config()
        cfg.validate()
        print("Success (unexpected)")
    except ValueError as e:
        print(f"Caught ValueError: {e}")
    except Exception as e:
        print(f"Caught {type(e).__name__}: {e}")
    finally:
        if "MAX_TOKENS" in os.environ:
            del os.environ["MAX_TOKENS"]


if __name__ == "__main__":
    test_config_invalid_env_var()
