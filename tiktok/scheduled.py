"""Run the private collector with bounded logs and no interactive sign-in."""
import logging
from logging.handlers import RotatingFileHandler
import os
from client import ROOT, private_dir
from collect import main

if __name__=='__main__':
    os.umask(0o077)
    handler=RotatingFileHandler(private_dir(ROOT/'logs')/'collector.log',maxBytes=262144,backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger=logging.getLogger('tiktok')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info('Scheduled TikTok collection started')
    try:
        main()
    except BaseException as exc:
        logger.error('Collection failed: %s; inspect private status.json',type(exc).__name__)
        raise SystemExit(1)
    logger.info('Collection succeeded')
