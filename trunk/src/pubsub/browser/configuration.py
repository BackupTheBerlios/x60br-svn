import gtk

from twisted.words.protocols.jabber import xmlstream
from twisted.words.xish import domish

from pubsub.browser.utils import DISCO_ITEMS_NS, GLADE_FILE, PUBSUB_NS
from pubsub.browser.utils import PUBSUB_OWNER_NS, JABBER_X_DATA_NS, print_err
from pubsub.browser.fields import field_from_xml

class NodeConfigurationDlg:
    
    def __init__(self,xmlstream,node,component):
        self.xmlstream = xmlstream
        self.node = node
        tree = gtk.glade.XML(GLADE_FILE,"nodeConfigurationDlg") 
        
        tree.signal_autoconnect({"response" : self._on_response}  )
        
        self.dlg = tree.get_widget("nodeConfigurationDlg")
        self.table = tree.get_widget("table")
        self.component = component
        d = self._send_pubsub_conf_request(node)
        self.dlg.set_title(node.name)
        d.addCallback(self._on_data_form)
        d.addErrback(print_err)
    
    def show(self):
        self.dlg.show()
    
    def _send_pubsub_conf_request(self,node):
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        query.addChild(domish.Element((None,'configure'),attribs={'node':node.name}))
        iq = xmlstream.IQ(self.xmlstream,"get")
        iq.addChild(query)
        d =iq.send(to=self.component)
        return d
    
    def _on_data_form(self,resp):
        print resp.toXml()
        self.fields = []
        graphicals = []
        form = resp.firstChildElement().firstChildElement().firstChildElement()
        for field_xml in form.elements():
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
        table.resize(len(graphicals),2)
        for field in graphicals:
            label = gtk.Label(field.get_label())
            label.set_alignment(0, 0.5)
            widget = field.get_widget()
            table.attach(label, 0, 1, row, row +1, xoptions=gtk.FILL, yoptions=gtk.FILL)
            table.attach(widget,1,2,row,row+1,xoptions=gtk.FILL, yoptions=gtk.FILL)
            label.show()
            widget.show()
            row = row+1
        table.show()    
        
        
    def _on_response(self,dlg,resp):
        if  resp == gtk.RESPONSE_OK:
            fields = [field.read_to_xml() for field in self.fields]
            d = self._send_pubsub_configurtion(fields)
            d.addCallback(lambda _ : self.dlg.destroy())
            d.addErrback(print_err)
        else:
            self._send_cancel()
            self.dlg.destroy()
            
    def _send_cancel(self):
        pass
        """
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        cfg = domish.Element((None,'configure'),attribs={'node':self.node})
        query.addChild(cfg)
        form = domish.Element((JABBER_X_DATA_NS,'x'),attribs={'type':'cancel'})
        iq = xmlstream.IQ(self.xmlstream,"set")
        iq.addChild(query)
        iq.send(to=self.component)
        """
        
        

    def _send_pubsub_configurtion(self,fields_xml):
        query = domish.Element((PUBSUB_OWNER_NS,"pubsub"))
        cfg = domish.Element((None,'configure'),attribs={'node':self.node.name})
        query.addChild(cfg)
        form = domish.Element((JABBER_X_DATA_NS,'x'),attribs={'type':'submit'})
        cfg.addChild(form)
        for field in fields_xml:
            form.addChild(field)
            
        
        iq = xmlstream.IQ(self.xmlstream,"set")
        iq.addChild(query)
        d =iq.send(to=self.component)
        return d
