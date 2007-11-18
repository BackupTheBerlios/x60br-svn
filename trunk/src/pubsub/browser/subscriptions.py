import gtk

from twisted.words.protocols.jabber import xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, GLADE_FILE, PUBSUB_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS, print_err



class NodeSubscriptionsDlg:
    def __init__(self,xmlstream,node,component):
        self.xmlstream = xmlstream
        self.node = node
        self.component = component
        tree = gtk.glade.XML(GLADE_FILE,"nodeSubscriptionsDlg") 
        self.dlg = tree.get_widget("nodeSubscriptionsDlg") 
        self.dlg.set_title(node)
        view = tree.get_widget("subscriptions_tree")
        model = gtk.ListStore(str,str)
        view.set_model(model)
        jid_col = gtk.TreeViewColumn("JID",gtk.CellRendererText(),text=0)
        subs_col = gtk.TreeViewColumn("Subscription",gtk.CellRendererText(),text=1)
        view.append_column(jid_col)
        view.append_column(subs_col)
        view.set_headers_visible(True)
        self.model = model
        self.tree_selection = view.get_selection()
       
        treePopup = gtk.glade.XML(GLADE_FILE,"delete_popup") 
        self.delete_popup = treePopup.get_widget("delete_popup")
        treePopup.signal_autoconnect({'on_delete_activate': lambda _ : self._on_delete()})
        
        tree.signal_autoconnect({"response" : self._on_response,
                                 "on_subscriptions_tree_button_press_event": self._on_subscriptions_tree_button_press_event})
        self.refresh()
        
    def _on_delete(self):
        model,iter = self.tree_selection.get_selected()
        if iter is not None:
            jid = model.get_value(iter,0)
            d = self._send_pubsub_modify_subscription(self.node, jid, 'none')
            d.addCallback(lambda _ : self.refresh())
            d.addErrback(print_err)
            
    def _on_subscriptions_tree_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.delete_popup.popup( None, None, None, event.button, time)
        return 0
        
    
    def _on_response(self,dlg,resp):
        if resp == 2 :  #refresh
            self.refresh()
        elif resp == 3:  #add 
            self._on_new_subs()
        else:
            self.dlg.destroy()
            
    def _on_new_subs(self):
        print "new subscription"
        """
        gladefile = "gui/gui2.glade/gui2.glade.glade"
        newAffiliationTree = gtk.glade.XML(gladefile,"newAffiliationDlg") 
        self.newAffDlg =   newAffiliationTree.get_widget("newAffiliationDlg")
        
        
        def on_dlg_response(dlg,resp):
            if resp == gtk.RESPONSE_OK:
                jid = newAffiliationTree.get_widget('jid').get_text()
                affiliation = 'owner'
                if newAffiliationTree.get_widget('publisher').get_active():
                    affiliation = 'publisher'
                d = self._send_pubsub_modify_affiliation(self.node, jid, affiliation)
                d.addCallback(lambda _ : self.refresh())
                d.addErrback(print_err)
            dlg.destroy()
            
        newAffiliationTree.signal_autoconnect({'response' : on_dlg_response})
        self.newAffDlg.show()
        """
    
    def _send_pubsub_subscriptions_request(self,node):
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        query.addChild(domish.Element((None,'subscriptions'),attribs={'node':node}))
        iq = xmlstream.IQ(self.xmlstream,"get")
        iq.addChild(query)
        print iq.toXml()
        d =iq.send(to=self.component)
        print "request enviado"
        return d
    
    def _on_subscriptions(self,resp):
        subscriptions = resp.firstChildElement().firstChildElement()
        for subscription in subscriptions.elements():
            self.model.append((subscription['jid'],subscription['subscription']))
        
    def refresh(self):
        self.model.clear()
        d = self._send_pubsub_subscriptions_request(self.node)
        d.addCallback(self._on_subscriptions)
        d.addErrback(print_err)
        
        
    def _send_pubsub_modify_subscription(self,node,jid,subscription):
        print "modify subscriptions"
        req = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        affiliations = domish.Element((None,'subscriptions'),attribs={'node':node})
        req.addChild(affiliations)
        affiliations.addChild(domish.Element((None,'subscription'),attribs={
                                                                       'jid':jid,
                                                                       'subscription':subscription    
                                                                           }))
        
        iq = xmlstream.IQ(self.xmlstream,"set")
        iq.addChild(req)
        print iq.toXml()
        d =iq.send(to=self.component)
        print "request enviado"
        return d

        
    def show(self):
        self.dlg.show()
