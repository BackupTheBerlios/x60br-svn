import gtk

from twisted.words.protocols.jabber import xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, GLADE_FILE, PUBSUB_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS, print_err
from pubsub.browser.utils import PUBSUB_NODE_CONFIG_NS
from pubsub.browser.fields import field_from_xml


class CreateNodeDlg:
    def __init__(self,mainapp,on_response):
        self.xmlstream = mainapp.xmlstream
        self.component = mainapp.component
        self.mainapp = mainapp
        self.on_response = on_response
        tree = gtk.glade.XML(GLADE_FILE,"createNodeDlg") 
        
        tree.signal_autoconnect({"response" : self._on_response,
                                 "instant_node_toggled" : self._on_instant_node_toggled,
                                 'on_node_type_changed' : self._on_node_type_changed}  )
       
       
        self.leaf = tree.get_widget('leaf') 
        self.dlg = tree.get_widget("createNodeDlg")
        self.table = tree.get_widget("table")
        self.node_name_box = tree.get_widget("node_name_box")
        self.node_name = tree.get_widget("node_name")
        self.instant_node = tree.get_widget("instant_node")
    
        
        self._request_leaf_form()
        self.fields = []
    
    def show(self):   
        self.dlg.show()
       
    def _on_instant_node_toggled(self,instant_node):
        if instant_node.get_active():
            self.node_name_box.hide()
        else:
            self.node_name_box.show()
        
       
    def get_name(self): 
        if not self.instant_node.get_active():
            return self.node_name.get_text()
        else:
            return None

    def get_leaf(self):
        return self.leaf.get_active()

    def get_fields(self):
        return self.fields
       
        

    def _on_response(self,dlg,resp):
       # 
       #if resp == gtk.RESPONSE_OK:
       #    self._create_node()
       self.on_response(self,resp)    
       self.dlg.destroy()
       
    def _request_leaf_form(self):
        ps = domish.Element((PUBSUB_OWNER_NS,'pubsub'))
        ps.addElement((None,'default'))
        iq = xmlstream.IQ(self.xmlstream,"get")
        iq.addChild(ps)
        #print iq.toXml()
        d = iq.send(to=self.component)
        d.addCallback(self._show_form)
        d.addErrback(print_err)
        
        
    def _show_form(self,resp):
        print resp.toXml()
        self.fields = []
        graphicals = []
        form = resp.firstChildElement().firstChildElement().firstChildElement()
        #print form.name
        for field_xml in form.elements():
            print 'field_xml'
            try:
                field = field_from_xml(field_xml)
            except KeyError:
                pass
            else:
                if field.is_graphical():
                    graphicals.append(field)
                self.fields.append(field)
        
        table = self.table
        row = 0
        #print graphicals
        table.resize(len(graphicals),2)
        for field in graphicals:
            label = gtk.Label(field.get_label())
            widget = field.get_widget()
            table.attach(label, 0, 1, row, row +1)
            table.attach(widget,1,2,row,row+1)
            label.show()
            widget.show()
            row = row+1


    def _request_collection_form(self):
        ps = domish.Element((PUBSUB_OWNER_NS,'pubsub'))
        default = ps.addElement((None,'default'))
        
        
        form = domish.Element((JABBER_X_DATA_NS,'x'),attribs={'type':'submit'})
        field = domish.Element((None,'field'),attribs={'var':'FORM_TYPE',
                                                        'type':'hidden'})
        field.addElement((None,'value'),content=PUBSUB_NODE_CONFIG_NS)
        form.addChild(field)
        default.addChild(form)
        iq = xmlstream.IQ(self.xmlstream,"get")
        iq.addChild(ps)
        print iq.toXml()
        d = iq.send(to=self.component)
        d.addCallback(self._show_form)
        d.addErrback(print_err)
        
         

    def _on_node_type_changed(self,group):
        for widget in self.table.get_children():
            self.table.remove(widget)
        if self.leaf.get_active():
            self._request_leaf_form()
        else:
            self._request_collection_form()
       