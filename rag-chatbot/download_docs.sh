git clone --no-checkout --depth=1 --filter=tree:0 \
  https://github.com/scylladb/scylladb.git
cd scylladb
git sparse-checkout set --no-cone /docs
git checkout
