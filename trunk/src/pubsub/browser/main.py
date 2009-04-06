import gobject
import gtk
import gtk.gdk
import gtk.glade





from twisted.internet import gtk2reactor # for gtk-2.0
gtk2reactor.install()

from twisted.internet import reactor,defer


from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, GLADE_FILE, PUBSUB_NS, DISCO_INFO_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS, print_err


from pubsub.browser.affiliations import NodeAffiliationsDlg
from pubsub.browser.configuration import NodeConfigurationDlg
from pubsub.browser.subscriptions import NodeSubscriptionsDlg
from pubsub.browser.createnode import CreateNodeDlg

        
        
from pubsub import pubsubapi

class ShowItemsDlg:
    def __init__(self, Element):
        tree = gtk.glade.XML(GLADE_FILE,"showItemsDlg") 
        
        tree.signal_autoconnect({"on_response" : self._on_response})
        self.dlg = tree.get_widget("showItemsDlg")
        tree.get_widget("text").get_buffer().set_text(Element.toXml())
    
    def show(self):   
        self.dlg.show()
   
    def _on_response(self,dlg,resp):
        self.dlg.destroy()
       
        

class Browser:
    def __init__(self,xmlstream,component):
        tree = gtk.glade.XML(GLADE_FILE,"mainWindow") 
        window = tree.get_widget("mainWindow")
        window.show()
        self.xmlstream = xmlstream
        self.component = component
        print xmlstream,component
        
        self.pubsub = pubsubapi.PubSub(xmlstream, component)
        
        def create_top_level():
            self._on_create_on_parent(None)
        
        tree.signal_autoconnect({"window_destroy" : lambda _ : reactor.stop(),
                                 "on_node_tree_button_press_event" : self._on_node_tree_button_press_event,
                                 "on_force_refresh_clicked" : lambda _ : reactor.callFromThread(self.refresh_tree),
                                 "on_new_toplevel_node_button_clicked" : lambda _ : create_top_level(),
                                 "on_change_component_button_clicked" : self._on_change_component
                                 })


        node_view = tree.get_widget("node_tree")
        
        tree.get_widget("pubsub_component_entry").set_text(component)
        
        node_view.get_selection().connect("changed",self._on_selection_changed)
        
        self.tree_selection = node_view.get_selection()
        
        node_col = gtk.TreeViewColumn("Node")
       
        nodeIconRenderer = gtk.CellRendererPixbuf()
        node_col.pack_start(nodeIconRenderer, expand=False)
        node_col.add_attribute(nodeIconRenderer,'pixbuf',1)
       
        nodeTextRenderer = gtk.CellRendererText()
        node_col.pack_start(nodeTextRenderer, expand=False)
        node_col.add_attribute(nodeTextRenderer,'text',2) 
        
        node_view.append_column(node_col)
        
        # model is : (node,icon,name) 
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT,gobject.TYPE_OBJECT, str)
        node_view.set_model(self.model)
        
        treePopup = gtk.glade.XML(GLADE_FILE,"node_popup") 
        self.node_popup = treePopup.get_widget("node_popup")
        
        
        self.add_child_menu = treePopup.get_widget("add_child")
        treePopup.signal_autoconnect({ "on_configure_activate" : self._on_configure_node,
                                      "on_affiliations_activate" : self._on_node_affiliations,
                                      "on_subscriptions_activate" : self._on_node_subscriptions,
                                      "on_delete_node_activate":self._on_delete_node,
                                      "on_add_child_activate" : self._on_create_node,
                                      "on_publish_item_activate" : self._on_publish_item,
                                      "on_getitems_activate" : self._on_get_items
                                      })

        
        self.collection_node_pixbuf = gtk.gdk.pixbuf_new_from_file('gui/collection_node.png')
        self.leaf_node_pixbuf = gtk.gdk.pixbuf_new_from_file('gui/leaf_node.png')
    
        self.mapping = {}
        self.tree = tree
        self.refresh_tree()
        

    def _selected_node(self):
        model,iter = self.tree_selection.get_selected()
        if iter is not None:
            return model.get_value(iter,0)
        return None
            

                               
    def _on_node_tree_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                iter = self.model.get_iter(path)
                if self.model.get_value(iter,0).type == 'collection':
                    self.add_child_menu.show()
                else:
                    self.add_child_menu.hide()
                self.node_popup.popup( None, None, None, event.button, time)
            #else:
            #    self.node_popup.popup( None, None, None, event.button, time)
        return 0
    
    def _on_selection_changed(self,tree_selection):
        node = self._selected_node()
        if node is not None:
            print node.name


    def _on_node_affiliations(self,evt):
        selected = self._selected_node()
        if selected is not None:
            dlg = NodeAffiliationsDlg(self.xmlstream,selected,self.component)
            dlg.show()
            
    def _on_node_subscriptions(self,evt):
        selected = self._selected_node()
        if selected is not None:
            dlg = NodeSubscriptionsDlg(self.xmlstream,selected,self.component)
            dlg.show()
    
    def _on_get_items(self, evt):
        def response(Element):
            dlg = ShowItemsDlg(Element)
            dlg.show()
            
        selected = self._selected_node()
        if selected is not None:
            d = selected.get_items()
            d.addCallback(response)
            d.addErrback(print_err)


    def _on_configure_node(self,evt):
        selected = self._selected_node()
        if selected is not None:
            dlg = NodeConfigurationDlg(self.xmlstream,selected,self.component)
            dlg.show()
            
            
    def _on_delete_node(self,evt):
        selected = self._selected_node()
        if selected is not None:
            d = selected.delete()
            def node_deleted(_):
                iter = self.mapping[selected]
                self.model.remove(iter)
                del self.mapping[selected]
            d.addCallback(node_deleted)
            d.addErrback(print_err)
         
         
    def _on_publish_item(self,evt):   
        selected = self._selected_node()
        dlgTree = gtk.glade.XML(GLADE_FILE,"publishItemDlg")
        dlg  = dlgTree.get_widget("publishItemDlg")
        
        
        def on_response(dlg,response):
            if response == gtk.RESPONSE_OK:
                text = dlgTree.get_widget("text")
                selected.publish(text.get_buffer().get_property("text"))
            dlg.destroy()
            
        dlgTree.signal_autoconnect({"response" : on_response})
        dlg.show()
        
        

    def _on_create_node(self,evt):
        selected = self._selected_node()
        if selected is not None:
            self._on_create_on_parent(selected)
        
    def _on_create_on_parent(self,parent):
        def on_response(dlg,response):
             if response == gtk.RESPONSE_OK:
                 name = dlg.get_name()
                 fields = [field.read_to_xml() for field in dlg.get_fields()]
                    
                 if dlg.get_leaf():
                     d = self.pubsub.create_leaf_node(name=name,
                                              parent_collection=parent,
                                              configuration_fields=fields) 
                 else:
                     d = self.pubsub.create_collection_node(name=name,
                                                parent_collection=parent,
                                                configuration_fields=fields)
                 d.addCallback(lambda node : self.node_created(parent,node))
                 d.addErrback(print_err)

        dlg = CreateNodeDlg(self,on_response)
        dlg.show()
        
        
    def _on_change_component(self, evt):
        component = self.tree.get_widget("pubsub_component_entry").get_text()
        self.pubsub.set_component(component)
        self.refresh_tree()
        

    def refresh_tree(self):
        self.model.clear()
        self.mapping = {}
        d = self.pubsub.get_root_nodes()
        
        def add_nodes(nodes,parent):
            for node in nodes:
                if node.type == "leaf":
                    iter = self.model.append(parent,(node,self.leaf_node_pixbuf,node.name))
                else:
                    iter = self.model.append(parent,(node,self.collection_node_pixbuf,node.name))
                    d = node.get_members()
                    d.addCallback(add_nodes,iter)
                    d.addErrback(print_err)
                self.mapping[node] = iter
            
        
        d.addCallback(add_nodes,None)
        d.addErrback(print_err)
        

    def node_created(self,parent,node):
        if parent is not None:
            parent_iter = self.mapping[parent]
        else:
            parent_iter = None
        if node.type == "leaf":
            self.mapping[node] = self.model.append(parent_iter,(node,self.leaf_node_pixbuf,node.name))
        else:
            self.mapping[node] = self.model.append(parent_iter,(node,self.collection_node_pixbuf,node.name))
        
        

class Login:
    def __init__(self):        
        tree = gtk.glade.XML(GLADE_FILE, "loginDlg") 
        self.dlg = tree.get_widget("loginDlg")
        self.username = tree.get_widget("login")
        self.password = tree.get_widget("password")
        self.host = tree.get_widget("host")
        self.port = tree.get_widget('port')
        self.component = tree.get_widget("component")
        self.msg = tree.get_widget("msg")
        tree.signal_autoconnect({"response" : self.on_response,
                                 "close" : lambda _1,_2: reactor.stop()
                                  } )

        
        self.username.set_text("pablo")
        self.password.set_text("pablo")
        self.host.set_text("localhost")
        self.component.set_text("pubsub")
        self.port.set_text('5222')
        
    
    def run(self):
        self.d = defer.Deferred()
        self.dlg.show()
        return self.d
        
    def on_response(self,dlg,resp):
       if  resp == gtk.RESPONSE_OK:
           host = self.host.get_text() 
           port = int(self.port.get_text())
           username = self.username.get_text()
           password = self.password.get_text()
           component = self.component.get_text()
           
           self.jid = jid.JID("%s@%s/Browser"% (username,host))
           factory = client.basicClientFactory(self.jid,password)
           factory.addBootstrap('//event/stream/authd',self.authenticated)
           factory.addBootstrap(client.BasicAuthenticator.INVALID_USER_EVENT, 
           self.login_error)
           factory.addBootstrap(client.BasicAuthenticator.AUTH_FAILED_EVENT, 
           self.login_error)
           reactor.connectTCP(host, port, factory)
       else:
           reactor.stop()

    def login_error(self,err):
       self.msg.set_text("Couldn't login")
       self.password.set_text("")
       
    
    def authenticated(self,xmlstream):
        component = ".".join((self.component.get_text(),self.host.get_text()))
        self.d.callback( (xmlstream,component) )
        self.dlg.destroy()
    

if __name__ == "__main__":
    l = Login()
    d = l.run()
    
        
    d.addCallback(lambda r : Browser(r[0],r[1]))
    reactor.run()
    
