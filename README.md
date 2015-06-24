virtualenv env
env/bin/source activate
STATIC_DEPS=true pip install lxml
pip install -r requirements.txt