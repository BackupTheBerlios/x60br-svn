import gtk
import gobject

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
        self.dlg.set_title(node.name)
        view = tree.get_widget("subscriptions_tree")
        model = gtk.ListStore(gobject.TYPE_PYOBJECT,str,str)
        view.set_model(model)
        jid_col = gtk.TreeViewColumn("JID",gtk.CellRendererText(),text=1)
        subs_col = gtk.TreeViewColumn("Subscription",gtk.CellRendererText(),text=2)
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
        
        self.mapping = {}
        self.refresh()
        
        
    def _get_selected(self):
        model,iter = self.tree_selection.get_selected()
        if iter is not None:
            return model.get_value(iter,0)
        return None
    
    def _on_delete(self):
        selected = self._get_selected()
        if selected is not None:
            d = self.node.remove_subscription(selected)
            def subscription_deleted(_):
                iter = self.mapping[selected]
                self.model.remove(iter)
                del self.mapping[selected]
            
            d.addCallback(subscription_deleted)
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
        gladefile = GLADE_FILE
        newSubscriptionTree = gtk.glade.XML(gladefile,"newSubscriptionDlg") 
        self.newSubsDlg =   newSubscriptionTree.get_widget("newSubscriptionDlg")
        def on_dlg_response(dlg,resp):
            if resp == gtk.RESPONSE_OK:
                jid = newSubscriptionTree.get_widget('jid').get_text()
                d = self.node.add_subscription(jid,'subscribed')
                def subscription_added(subscription):
                    self.mapping[subscription] = self.model.append((subscription,subscription.jid,subscription.subscription))
                d.addCallback(subscription_added)
                d.addErrback(print_err)
            dlg.destroy()
            
        newSubscriptionTree.signal_autoconnect({'response' : on_dlg_response})
        self.newSubsDlg.show()

    
    
        
    def refresh(self):
        self.model.clear()
        self.mapping = {}
        d = self.node.get_subscriptions()
        
        def _on_subscriptions(subscriptions):
            for subscription in subscriptions:
                self.mapping[subscription] = self.model.append((subscription,subscription.jid,subscription.subscription))
        
        d.addCallback(_on_subscriptions)
        d.addErrback(print_err)
        
        

        
    def show(self):
        self.dlg.show()
