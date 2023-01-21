"""config overrides. for full config run jupyter notebook –generate-config."""
# noqa to ignore undefined variable error
c.NotebookApp.allow_remote_access = True                   # noqa: F821
c.NotebookApp.certfile = '/home/ubuntu/certs/mycert.pem'   # noqa: F821
c.NotebookApp.ip = '*'                                     # noqa: F821
c.NotebookApp.open_browser = False                         # noqa: F821
c.NotebookApp.password = 'sha1:4158633c0a9f:5610ab9f8d5d7782dfb1a29145e671569d026df7'
