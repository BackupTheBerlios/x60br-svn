import gtk
import gobject

from twisted.words.protocols.jabber import xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, GLADE_FILE, PUBSUB_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS, print_err



class NodeAffiliationsDlg:
    def __init__(self,xmlstream,node,component):
        self.xmlstream = xmlstream
        self.node = node
        self.component = component
        tree = gtk.glade.XML(GLADE_FILE,"nodeAffiliationsDlg") 
        self.dlg = tree.get_widget("nodeAffiliationsDlg") 
        self.dlg.set_title(node.name)
        view = tree.get_widget("affiliations_tree")
        model = gtk.ListStore(gobject.TYPE_PYOBJECT,str,str)
        view.set_model(model)
        jid_col = gtk.TreeViewColumn("JID",gtk.CellRendererText(),text=1)
        aff_col = gtk.TreeViewColumn("Affiliation",gtk.CellRendererText(),text=2)
        view.append_column(jid_col)
        view.append_column(aff_col)
        view.set_headers_visible(True)
        self.model = model
        self.tree_selection = view.get_selection()

       
        treePopup = gtk.glade.XML(GLADE_FILE,"delete_popup") 
        self.delete_popup = treePopup.get_widget("delete_popup")
        treePopup.signal_autoconnect({'on_delete_activate': lambda _ : self._on_delete()})
        
        tree.signal_autoconnect({"response" : self._on_response,
                                 "on_affiliations_tree_button_press_event": self._on_affiliations_tree_button_press_event})
        
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
            d = self.node.remove_affiliation(selected)
            def deleted(_):
                iter = self.mapping[selected]
                self.model.remove(iter)
                del self.mapping[selected]
            d.addCallback(deleted)
            d.addErrback(print_err)
            
    def _on_affiliations_tree_button_press_event(self, treeview, event):
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
            self._on_new_aff()
        else:
            self.dlg.destroy()
            
    def _on_new_aff(self):
        newAffiliationTree = gtk.glade.XML(GLADE_FILE,"newAffiliationDlg") 
        self.newAffDlg =   newAffiliationTree.get_widget("newAffiliationDlg")
        
        def on_dlg_response(dlg,resp):
            if resp == gtk.RESPONSE_OK:
                jid = newAffiliationTree.get_widget('jid').get_text()
                affiliation = 'owner'
                if newAffiliationTree.get_widget('publisher').get_active():
                    affiliation = 'publisher'
                d = self.node.add_affiliation(jid,affiliation)
                
                def do_add(affiliation):
                    self.mapping[affiliation] = self.model.append((affiliation,affiliation.jid,affiliation.affiliation))                    
                d.addCallback(do_add)
                d.addErrback(print_err)
            dlg.destroy()
            
        newAffiliationTree.signal_autoconnect({'response' : on_dlg_response})
        self.newAffDlg.show()
    
        
    def refresh(self):
        self.model.clear()
        self.mapping = {}
        d = self.node.get_affiliations()
        
        def _on_affiliations(affiliations):
            for affiliation in affiliations:
                self.mapping[affiliation] = self.model.append((affiliation,affiliation.jid,affiliation.affiliation))
    
        d.addCallback(_on_affiliations)
        d.addErrback(print_err)
        
        
        
    def show(self):
        self.dlg.show()
