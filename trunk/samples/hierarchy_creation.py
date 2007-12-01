from twisted.internet import reactor,defer

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish import domish

from pubsub.pubsubapi import PubSub



#Connection info
#Complete with appropiate data

HOST = "localhost"
PORT = 5222
USERNAME = "user"
PASSWORD = "pass"
PUBUSB_COMPONENT = "pubsub.localhost"


#hierarchy to create
COLLECTION = 1
LEAF = 2
hierarchy = [
             (COLLECTION,"collection1",[
                                        (COLLECTION,"collection1.1",[]),
                                        (LEAF,"node1.1"),
                                        (LEAF,"node1.2")
                                        ]),
             (LEAF,"node1"),
             (LEAF,"node2"),
             (COLLECTION,"collection2",[
                                        (LEAF,"node2.1")
                                        ]),
             (COLLECTION,"collection3",[
                                        (LEAF,"node3.1"),
                                        (LEAF,"node3.2"),
                                        (LEAF,"node3.3")
                                        ]),
             ]


# an <error logger> ;)
def log_err(err, msg=""):
    print "Error!: " , msg, err
    raise err #don't catch




def add_nodes(ps,nodes,parent_collection = None):
    if nodes == []: #nothing to do
        return defer.succeed(None)
    
    #array of pending responses from the server
    #used to fire a callback when all request have been fulfilled
    pending = [] 
    
    for node in nodes:
        print "Creating node ", node[1]
        if node[0] is LEAF:
            d = ps.create_leaf_node(node[1], parent_collection)
            d.addErrback(log_err,node[1])
            pending.append(d)
        else:
            d = defer.Deferred()
            d_collection = ps.create_collection_node(node[1], parent_collection)
            def create_childs(parent_node,parent_cb,childs):
                d_childs = add_nodes(ps,childs,parent_node)
                #when all childs have been created, fire the completion
                #of the parent's defer
                d_childs.chainDeferred(parent_cb)
                                
            #after the collection node is creaed, create all children
            d_collection.addCallback(create_childs,d,node[2])
            d_collection.addErrback(d.errback)
            d.addErrback(log_err,node[1])
            pending.append(d)
    return defer.DeferredList(pending,fireOnOneErrback=1, consumeErrors=1)




    
def authenticated(xmlstream):
    print "authenticated"
    ps = PubSub(xmlstream, PUBUSB_COMPONENT)
    d = add_nodes(ps,hierarchy)
    d.addErrback(log_err)
    d.addBoth(lambda _ : reactor.stop())
    

def login_error(err_msg):
       print "Couldn't login", err
       reactor.stop()
       
           
jid = jid.JID("%s@%s/Sample"% (USERNAME,HOST))
factory = client.basicClientFactory(jid,PASSWORD)
factory.addBootstrap('//event/stream/authd',authenticated)
factory.addBootstrap(client.BasicAuthenticator.INVALID_USER_EVENT, 
    login_error)
factory.addBootstrap(client.BasicAuthenticator.AUTH_FAILED_EVENT, 
    login_error)
reactor.connectTCP(HOST, PORT, factory)


reactor.run()

