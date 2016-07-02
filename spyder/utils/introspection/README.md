

Introspection is handled by `manager.IntrospectionManger`, which
in turn uses a `PluginManager` for each plugin.

The plugin manager uses a `PluginClient`, which creates a `QProcess`
managing a `PluginServer`.  The plugin server instantiates the plugin
and acts as a remote procedure call interface to the `PluginClient`.
Data is passed between the server and client as pickled objects over
bsd sockets.  We pass a request from:

 `Editor -> IntrospectionManager -> Plugin Manager -> PluginClient ->
  PluginServer -> Plugin`

The response bubbles back as:

 `Plugin -> PluginServer -> PluginClient -> PluginManager ->
  IntrospectionManager -> Editor`

There can only be one active and one pending request at a time.
There is a `LEAD_TIME_SEC` time where we wait for the primary response
from a request.  After that time, a secondary response can be used, or
a pending request will be sent, if there is one.

When a valid response reaches the `IntrospectionManager`, it checks
for the current state versus the state when the request was sent,
and decides how best to handle the response, to include ignoring it.
