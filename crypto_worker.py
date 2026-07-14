from market_worker import configure_logging, run_worker

if __name__ == "__main__":
    configure_logging("CRYPTO")
    run_worker("crypto")
