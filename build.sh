pyinstaller whisperninja/main.py \
  --windowed \
  --noconfirm \
  --name whisperninja \
  --add-data "whisperninja/assets:whisperninja/assets" \
  --add-data "whisperninja/config:whisperninja/config"