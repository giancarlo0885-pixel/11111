# Install the dual-worker upgrade

1. Upload every file in this ZIP into the root of the existing Hope-is-near GitHub repository and overwrite matching files.
2. Delete the old `database_upgrade.py` file from GitHub if it is still present.
3. In Railway, keep the existing Web service.
4. Create a Stock Worker service with start command `python stock_worker.py`.
5. Create a Crypto Worker service with start command `python crypto_worker.py`.
6. Copy the same PostgreSQL and API variables to all three services.
7. Set `STARTING_BALANCE=200` on all three services.
8. Redeploy all three services.

The dashboard will show a separate heartbeat for each worker.
