""" 
@author:Pablo Polvorin
@contact:pablo.polvorin@gmail.com


Functions for accessing a U{XEP-0060<http://www.xmpp.org/extensions/xep-0060.html>} service.
Most of the api is coded following the U{twisted<http://www.twistedmatrix.com>} asynchronous way; 
the methods perform an IQ call to the server and then return a Deferred, whitout blocking the caller. 

"""

import types
from twisted.internet import reactor,defer

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, PUBSUB_NS, DISCO_INFO_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS 



class Affiliation:
    """I represent an affiliation to a pubsub node"""
    def __init__(self,xml):
        if xml.name != 'affiliation':
            raise Exception("Expected an <affiliation/> element, got " + xml.name)
        self.xml = xml
        
    def get_jid(self):
        return self.xml['jid']
    
    def get_affiliation(self):
        return self.xml['affiliation']
    
    
    
    
    affiliation = property(get_affiliation,None)
    jid = property(get_jid,None)
        

class Subscription:
    """I represent a subscription to a pubsub node"""
    def __init__(self,xml):
        print xml.toXml()
        if xml.name != 'subscription':
            raise Exception("Expected an <affiliation/> element, got " + xml.name)
        self.xml = xml
        
    def get_jid(self):
        return self.xml['jid']
    
    def get_subscription(self):
        return self.xml['subscription']
    
    def has_subid(self):
        return self.xml.hasAttribute('subid')
    
    def get_subid(self):
        return self.xml['subid']
    
    subscription = property(get_subscription,None)
    jid = property(get_jid,None)
    subid = property(get_subid,None)
        
        

class PubSubNode:
    """A pubsub node as specified in XEP-0060"""
    def __init__(self,pubsub,node_name):
        self.pubsub = pubsub
        self.name = node_name
        
        
    def get_affiliations(self):
        """
        @rtype: list of L{Affiliation} (Deferred)
        """

        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        query.addChild(domish.Element((None,'affiliations'),attribs={'node':self.name}))
        d = self.pubsub.send_iq("get",query)
        
        def build_affiliations(resp):
            affiliations = resp.firstChildElement().firstChildElement()
            return [Affiliation(affiliation) for affiliation in affiliations.elements()]
        d.addCallback(build_affiliations)
        return d
    
    def get_subscriptions(self):
        """
        @rtype: list of L{Subscription} (Deferred)
        """
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        query.addChild(domish.Element((None,'subscriptions'),attribs={'node':self.name}))
        d = self.pubsub.send_iq("get",query)
        
        def build_subscriptions(resp):
            subscriptions = resp.firstChildElement().firstChildElement()
            return [Subscription(subscription) for subscription in subscriptions.elements()]
        d.addCallback(build_subscriptions)
        return d
    
    
    def remove_subscription(self,subscription):
        """
        @param subscription: subscription to remove
        @type subscription:  L{Subscription} or tuple (jid,subid)
        """
        if isinstance(subscription,Subscription):
            jid = subscription.jid
            if subscription.has_subid():
                subid = subscription.subid
            else:
                subid = None
            
        elif isintance(subscription,types.TupleType):
            jid,subid = subscription
        else:
            raise Exception("Wrong argument type, expected Subscription or tuple, get " + type(subscription))
            
        
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        subscriptions = domish.Element((None,'subscriptions'),attribs={'node':self.name})
        req.addChild(subscriptions)
        subs = subscriptions.addChild(domish.Element((None,'subscription'),attribs={
                                                                       'jid':jid,
                                                                       'subscription':'none'
                                                                           }))
        if subid is not None:
            subs['subid'] = subid
        d = self.pubsub.send_iq("set",req)
        return d

    
    
    def remove_affiliation(self,affiliation):    
        """
        @param affiliation: affiliation to remove
        @type affiliation: L{Affiliation} or str
        """
        if isinstance(affiliation,Affiliation):
            jid = affiliation.jid
        else:
            jid = affiliation
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        affiliations = domish.Element((None,'affiliations'),attribs={'node':self.name})
        req.addChild(affiliations)
        aff = affiliations.addChild(domish.Element((None,'affiliation'),attribs={
                                                                       'jid':jid,
                                                                       'affiliation':'none'    
                                                                           }))
        d = self.pubsub.send_iq("set",req)
        return d
        
    
        
    def add_affiliation(self,jid,affiliation):
        """
        @param jid: jid
        @type jid: str
        @param affiliation: affiliation
        @type affiliation: str
        @rtype: L{Affiliation}
        """
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        affiliations = domish.Element((None,'affiliations'),attribs={'node':self.name})
        req.addChild(affiliations)
        aff = affiliations.addChild(domish.Element((None,'affiliation'),attribs={
                                                                       'jid':jid,
                                                                       'affiliation':affiliation    
                                                                           }))
        d = self.pubsub.send_iq("set",req)
        d.addCallback(lambda _ : Affiliation(aff))
        return d

    
    def add_subscription(self,jid,subscription):
        """
        @param jid:jid
        @type jid: str
        @param subscription: subscription
        @type subscription: str
        @rtype: L{Subscription}
        """
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        subscriptions = domish.Element((None,'subscriptions'),attribs={'node':self.name})
        req.addChild(subscriptions)
        subs = subscriptions.addChild(domish.Element((None,'subscription'),attribs={
                                                                       'jid':jid,
                                                                       'subscription':subscription    
                                                                           }))
        d = self.pubsub.send_iq("set",req)
        
        #no subscription information in the response,
        #so use the submited element
        d.addCallback(lambda _ : Subscription(subs)) 
        
        return d
        
    
    def get_items(self):
        items = domish.Element((None,'items'), attribs={'node':self.name})
        req = domish.Element((PUBSUB_NS, "pubsub"))
        req.addChild(items)
        d = self.pubsub.send_iq("get",req)
        return d
                             
    
    def get_configuration_form(self):    
        pass
    
    def configure(self,configuration_form):
        pass
    
    
    def delete(self):
        """
        Delete this node.
        
        After a successfull call to this method, this object must be discarded
        """
        ps = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        ps.addChild(domish.Element((None,'delete'),attribs={'node' : self.name}))
        return self.pubsub.send_iq("set",ps)
       
    
    
    

class PubSubLeafNode(PubSubNode):
    type = 'leaf'
    def __init__(self,pubsub,node_name):
        PubSubNode.__init__(self,pubsub,node_name)
        
    def publish(self,item):
        """
        Used for testing only, will be refactored.
                 
        @param item: the item to publish
        @type item: str
        """
        ps = domish.Element((PUBSUB_NS,"pubsub"))
        publish = ps.addChild(domish.Element((None,'publish'),attribs={'node' : self.name}))
        if isinstance(item,types.ListType)  or isinstance(item,types.TupleType):
            for i in item:
                publish.addRawXml(i)
        else:
            publish.addRawXml(item)
            
            
        print ps.toXml()
        return self.pubsub.send_iq("set",ps)
       
        
    
    def __str__(self):
        return "[Leaf '" + self.name + "']"
    
    def __repr__(self):
        return "[Leaf '" + self.name + "']"



class PubSubCollectionNode(PubSubNode):
    type = 'collection'
    def __init__(self,pubsub,node_name):
        PubSubNode.__init__(self,pubsub,node_name)
        
    def get_members(self):
        return self.pubsub._get_child_nodes_of(self.name)
    
    def add_member(self,node):
        pass
    
    def remove_member(self,node):
        pass
    
    def __str__(self):
        return "[Collection '" + self.name + "']"
    
    def __repr__(self):
        return "[Collection '" + self.name + "']"
        



class PubSub:
    """
    Entry point to work with the api
    """
    def __init__(self,xmlstream,pubsub_component):  
        """
        @param pubsub_component: name of the pubsub component
        
        @param xmlstream: stream already connected and authenticated with the server
        @type xmlstream: xmlstream (twisted.words)
        """      
        self.xmlstream = xmlstream
        self.pubsub_component = pubsub_component
       
       
    def set_component(self, component):
        self.pubsub_component = component
        
    def _create_node(self,is_collection,name=None,parent_collection=None,configuration_fields=None):
        ps = domish.Element((PUBSUB_NS,"pubsub"))
        create = ps.addElement((None,'create'))
        
        if name is not None:
            create['node'] = name
        
        conf = ps.addElement((None,'configure'))
        
        
        form = domish.Element((JABBER_X_DATA_NS,'x'), attribs={'type':'submit'})
        if is_collection: 
            field = domish.Element((None,'field'),attribs={'var':'FORM_TYPE' , 'type': 'hidden'})
            field.addElement((None,'value'),content=PUBSUB_OWNER_NS)
            form.addChild(field)    
            field = domish.Element((None,'field'),attribs={'var':'pubsub#node_type'})            
            field.addElement((None,'value'),content='collection')
            form.addChild(field)
        
        if parent_collection is not None:
            field = domish.Element((None,'field'),attribs={'var':'pubsub#collection'})
            field.addElement((None,'value'),content=parent_collection.name)
            form.addChild(field)
        
        
        
        if configuration_fields is not None:
            for field in configuration_fields:
                form.addChild(field)
        
        conf.addChild(form)
        
        
        return self.send_iq("set", ps)
        
        
        
    
        
    def create_collection_node(self,name=None,parent_collection=None,configuration_fields=None):
        """
        Creates a collection pubsub node.

        @type parent_collection: L{PubSubCollectionNode}
        
        @rtype: L{PubSubCollectionNode} (Deferred)
        @return: The created node

        """
        def node_created(resp):
            try:
                assigned_name = resp.pubsub.create['node']
            except:
                assigned_name = name
            if assigned_name is None:
                raise Exception("Couldn't determine nodeId for the generated node")
            return PubSubCollectionNode(self,assigned_name) 
        
        d = self._create_node(True, name, parent_collection, configuration_fields)
        d.addCallback(node_created)
        return d

    def create_leaf_node(self,name=None,parent_collection=None,configuration_fields=None):
        """
        Creates a leaf pubsub node.
        
        If name is not given, the server will assign one. 
        Note that even when a name is explicitly supplied, 
        the resulting node can still get a different one, 
        as the server is allowed to change it. 

        @type parent_collection: L{PubSubCollectionNode}
        
       
        @return: The created node
        @rtype: L{PubSubLeafNode} (Deferred)        
        """
        def node_created(resp):
            try:
                assigned_name = resp.pubsub.create['node']
            except:
                assigned_name = name
            if assigned_name is None:
                raise Exception("Couldn't determine nodeId for the generated node")
            return PubSubLeafNode(self,assigned_name) #todo: sacar el nombre del xml
        
        d = self._create_node(False, name, parent_collection, configuration_fields)
        d.addCallback(node_created)
        return d
    


    def _get_node(self,node_name):
        query = domish.Element((DISCO_INFO_NS,"query"),attribs={'node' : node_name})
        d = self.send_iq("get", query)
        def build_node_from_info(resp):
            for item in resp.firstChildElement().elements():
                if item.name == 'identity' and item['category'] == 'pubsub':
                    if item['type'] == 'collection':
                        return PubSubCollectionNode(self, node_name)
                    elif item['type'] == 'leaf':
                        return PubSubLeafNode(self, node_name)
                    else:
                        raise Exception("Unknown node-type:", item['type'])
            raise Exception("no node-type information")        
        d.addCallback(build_node_from_info)
        return d
        
        
    def _get_child_nodes_of(self,node_name):        
        query = domish.Element((DISCO_ITEMS_NS,"query"))
        if node_name is not None:
            query['node'] = node_name
        d = self.send_iq("get", query)
        response = defer.Deferred()
        def on_nodes(resp):
            defer_list = []
            for item in resp.firstChildElement().elements():
                d2 = self._get_node(item['node'])
                defer_list.append(d2)
            
            f = defer.DeferredList(defer_list,consumeErrors=True)
            f.chainDeferred(response)
        
        d.addCallback(on_nodes)
        d.addErrback(response.errback)
        
        response.addCallback(lambda l : [n for (success,n) in l if success == True ])
        return response
        
    def get_root_nodes(self):
        """
        @return: list of top-level nodes 
        @rtype: list L{PubSubNode} (Deferred)
        """
        return self._get_child_nodes_of(None)
        
    
    def send_iq(self,type,iq_child):
        iq = xmlstream.IQ(self.xmlstream,type)
        iq.addChild(iq_child)
        d =iq.send(to=self.pubsub_component)
        return d 
    


