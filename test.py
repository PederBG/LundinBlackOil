from snappy import EngineConfig
print('tileCachSize', EngineConfig.instance().preferences().get('snap.jai.tileCacheSize', None))