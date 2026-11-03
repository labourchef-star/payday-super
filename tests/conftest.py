import os,sys,tempfile
os.environ["DB_PATH"]=tempfile.mktemp(suffix=".db"); os.environ.pop("DATABASE_URL",None)
os.environ["DEV_SHOW_CODES"]="1"; os.environ["SECURE_COOKIES"]="0"; os.environ["METRICS_TOKEN"]="mtok"
os.environ["GUMROAD_PRODUCT_IDS"]="TESTPROD"; os.environ["GUMROAD_ACCESS_TOKEN"]="gt"; os.environ.pop("RESEND_API_KEY",None)
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
