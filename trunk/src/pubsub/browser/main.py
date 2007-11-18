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

        
        
    


        

class Browser:
    def __init__(self,xmlstream,component):
        tree = gtk.glade.XML(GLADE_FILE,"mainWindow") 
        window = tree.get_widget("mainWindow")
        window.show()
        self.xmlstream = xmlstream
        self.component = component
        
        def create_top_level():
            dlg = CreateNodeDlg(self,None)
            dlg.show()
        
        tree.signal_autoconnect({"window_destroy" : lambda _ : reactor.stop(),
                                 "on_node_tree_button_press_event" : self._on_node_tree_button_press_event,
                                 "on_force_refresh_clicked" : lambda _ : reactor.callFromThread(self.refresh_tree),
                                 "on_new_toplevel_node_button_clicked" : lambda _ : create_top_level()
                                 })

        node_view = tree.get_widget("node_tree")
        
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
        
        # model is : (is_collection,icon,name) 
        self.model = gtk.TreeStore(gobject.TYPE_BOOLEAN,gobject.TYPE_OBJECT, str)
        node_view.set_model(self.model)
        
        treePopup = gtk.glade.XML(GLADE_FILE,"node_popup") 
        self.node_popup = treePopup.get_widget("node_popup")
        
        
        self.add_child_menu = treePopup.get_widget("add_child")
        treePopup.signal_autoconnect({ "on_configure_activate" : self._on_configure_node,
                                      "on_affiliations_activate" : self._on_node_affiliations,
                                      "on_subscriptions_activate" : self._on_node_subscriptions,
                                      "on_delete_node_activate":self._on_delete_node,
                                      "on_add_child_activate" : self._on_create_node,
                                      })

        
        self.collection_node_pixbuf = gtk.gdk.pixbuf_new_from_file('gui/collection_node.png')
        self.leaf_node_pixbuf = gtk.gdk.pixbuf_new_from_file('gui/leaf_node.png')
    
        self.refresh_tree()
        

    def _selected_node(self):
        model,iter = self.tree_selection.get_selected()
        if iter is not None:
            return model.get_value(iter,2)
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
                if self.model.get_value(iter,0):
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
            print node


    def _on_node_affiliations(self,evt):
        selected = self._selected_node()
        if selected is not None:
            print "affiliations:",selected
            dlg = NodeAffiliationsDlg(self.xmlstream,selected,self.component)
            dlg.show()
            
    def _on_node_subscriptions(self,evt):
        selected = self._selected_node()
        if selected is not None:
            print "affiliations:",selected
            dlg = NodeSubscriptionsDlg(self.xmlstream,selected,self.component)
            dlg.show()
        



    def _on_configure_node(self,evt):
        selected = self._selected_node()
        if selected is not None:
            print "configuring:",selected
            dlg = NodeConfigurationDlg(self.xmlstream,selected,self.component)
            dlg.show()
            
            
    def _on_delete_node(self,evt):
        selected = self._selected_node()
        if selected is not None:
            print "deleting:",selected
            d = self._send_iq_delete_node(selected)
            d.addCallback(lambda _ : self.refresh_tree())
            d.addErrback(print_err)
            

    def _on_create_node(self,evt):
        selected = self._selected_node()
        if selected is not None:
            print 'creating  on :', selected
            dlg = CreateNodeDlg(self,selected)
            dlg.show()
        
        
        
    def _send_iq_disco_items(self,node = None):
        query = domish.Element((DISCO_ITEMS_NS,"query"))
        if node is not None:
            query['node'] = node
        iq = xmlstream.IQ(self.xmlstream,"get")
        iq.addChild(query)
        d =iq.send(to=self.component)
        return d
  
        

    
    def _send_iq_delete_node(self,node_name):
        ps = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        ps.addChild(domish.Element((None,'delete'),attribs={'node' : node_name}))
        iq = xmlstream.IQ(self.xmlstream,"set")
        iq.addChild(ps)
        return iq.send(to = self.component)
        
        
    
    
    def refresh_tree(self):
        self.model.clear()
        d = self._send_iq_disco_items()
        d.addCallback(self._on_disco_items_response,None)
        d.addErrback(print_err)
        
        
        
    def _request_node_info(self,node):
        query = domish.Element((DISCO_INFO_NS,"query"),attribs={'node' : node})
        iq = xmlstream.IQ(self.xmlstream,"get")
        iq.addChild(query)
        return iq.send(to = self.component)


    def _on_disco_info_response(self,iq_resp,node,parent):
        """
        Add the node to the model.
        If the node is a collection node, do a disco#items to request  
        children nodes.
        """
        for item in iq_resp.firstChildElement().elements():
            if item.name == 'identity' and item['category'] == 'pubsub':
                if item['type'] == 'collection':
                    iter = self.model.append(parent,(True,self.collection_node_pixbuf,node))
                    d = self._send_iq_disco_items(node)
                    d.addCallback(self._on_disco_items_response,iter)
                    d.addErrback(print_err)
                elif item['type'] == 'leaf':
                    self.model.append(parent,(False,self.leaf_node_pixbuf,node))
                else:
                    print "Unknown node-type:", item['type']
                return
        
        print "invalid disco info response"
                
        

    def _on_disco_items_response(self,iq_resp,parent):
        """
        For each node, request the node info
        """
        model = self.model
        for item in iq_resp.firstChildElement().elements():
            d2 = self._request_node_info(item['node'])
            d2.addCallback(self._on_disco_info_response,item['node'],parent)
            d2.addErrback(print_err)
            
            
        



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

        #self.username.set_text("pablo")
        #self.password.set_text("pablo")
        #self.host.set_text("pablo-desktop")
        #self.component.set_text("pubsub")
        #self.port.set_text('5225')
    
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
    