#from twisted.internet import gtk2reactor # for gtk-2.0
#gtk2reactor.install()

from twisted.internet import reactor,defer


from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, GLADE_FILE, PUBSUB_NS, DISCO_INFO_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS, print_err



class Affiliation:
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
    def __init__(self,xml):
        if xml.name != 'subscription':
            raise Exception("Expected an <affiliation/> element, got " + xml.name)
        self.xml = xml
        
    def get_jid(self):
        return self.xml['jid']
    
    def get_subscription(self):
        return self.xml['subscription']
    
    
    subscription = property(get_subscription,None)
    jid = property(get_jid,None)
        
        

class PubSubNode:
    def __init__(self,pubsub,node_name):
        self.pubsub = pubsub
        self.name = node_name
        
        
        
    def get_affiliations(self):
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        query.addChild(domish.Element((None,'affiliations'),attribs={'node':self.name}))
        d = self.pubsub.send_iq("get",query)
        
        def build_affiliations(resp):
            affiliations = resp.firstChildElement().firstChildElement()
            return [Affiliation(affiliation) for affiliation in affiliations.elements()]
        d.addCallback(build_affiliations)
        return d
    
    def get_subscriptions(self):
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        query.addChild(domish.Element((None,'subscriptions'),attribs={'node':self.name}))
        d = self.pubsub.send_iq("get",query)
        
        def build_subscriptions(resp):
            subscriptions = resp.firstChildElement().firstChildElement()
            return [Subscription(subscription) for subscription in subscriptions.elements()]
        d.addCallback(build_subscriptions)
        return d
    
    
    def remove_subscription(self,subscription):
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        subscriptions = domish.Element((None,'subscriptions'),attribs={'node':self.name})
        req.addChild(subscriptions)
        subs = subscriptions.addChild(domish.Element((None,'subscription'),attribs={
                                                                       'jid':subscription.jid,
                                                                       'subscription':'none'
                                                                           }))
        d = self.pubsub.send_iq("set",req)
        return d

    
    
    def remove_affiliation(self,affiliation):    
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        affiliations = domish.Element((None,'affiliations'),attribs={'node':self.name})
        req.addChild(affiliations)
        aff = affiliations.addChild(domish.Element((None,'affiliation'),attribs={
                                                                       'jid':affiliation.jid,
                                                                       'affiliation':'none'    
                                                                           }))
        d = self.pubsub.send_iq("set",req)
        return d
        
    
        
    def add_affiliation(self,jid,affiliation):
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
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        subscriptions = domish.Element((None,'subscriptions'),attribs={'node':self.name})
        req.addChild(subscriptions)
        subs = subscriptions.addChild(domish.Element((None,'subscription'),attribs={
                                                                       'jid':jid,
                                                                       'subscription':subscription    
                                                                           }))
        d = self.pubsub.send_iq("set",req)
        d.addCallback(lambda _ : Subscription(subs))
        return d
        
    
    def get_configuration_form(self):    
        pass
    
    def configure(self,configuration_form):
        pass
    
    
    def delete(self):
        ps = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        ps.addChild(domish.Element((None,'delete'),attribs={'node' : self.name}))
        return self.pubsub.send_iq("set",ps)
       
    
    
    

class PubSubLeafNode(PubSubNode):
    type = 'leaf'
    def __init__(self,pubsub,node_name):
        PubSubNode.__init__(self,pubsub,node_name)
        
    def publish(self,item):
        pass
    
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
    def __init__(self,xmlstream,pubsub_component):        
        self.xmlstream = xmlstream
        self.pubsub_component = pubsub_component
       
       
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
        d.addErrback(print_err)
        return d

    def create_leaf_node(self,name=None,parent_collection=None,configuration_fields=None):
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
        d.addErrback(print_err)
        return d
    


    def _get_node(self,node_name):
        query = domish.Element((DISCO_INFO_NS,"query"),attribs={'node' : node_name})
        d = self.send_iq("get", query)
        print "_get_node 1"
        def build_node_from_info(resp):
            print "nuild_from_node_info"
            for item in resp.firstChildElement().elements():
                if item.name == 'identity' and item['category'] == 'pubsub':
                    if item['type'] == 'collection':
                        return PubSubCollectionNode(self, node_name)
                    elif item['type'] == 'leaf':
                        return PubSubLeafNode(self, node_name)
                    else:
                        raise Exception("Unknown node-type:", item['type'])
            raise Exception("no node-type information")        
        print "_get_node 2"
        d.addCallback(build_node_from_info)
        d.addErrback(print_err)
        print "_get_node 3"
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
        return self._get_child_nodes_of(None)
        
    
    def send_iq(self,type,iq_child):
        iq = xmlstream.IQ(self.xmlstream,type)
        iq.addChild(iq_child)
        d =iq.send(to=self.pubsub_component)
        return d 
    


