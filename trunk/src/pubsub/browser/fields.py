import gtk
from twisted.words.xish import domish

class Field:
    def __init__(self,xml):
        self.var = xml['var']
        
    def read_to_xml(self):
        return domish.Element((None,'field'),attribs={'var' : self.var})

class HiddenField(Field):
    def __init__(self,xml):
        Field.__init__(self,xml)
        self.xml = xml

        
    def get_widget(self):
        return None
    
    def get_label():
        return None
    
    def read_to_xml(self):  
        return self.xml  
    
    def is_graphical(self):
        return False

class LabeledField(Field):
    def __init__(self,xml):
        Field.__init__(self,xml)
        self.label = xml['label']
        
    def get_label(self):
        return self.label

    def is_graphical(self):
        return True
        
    
class BooleanField(LabeledField):
    def __init__(self,xml):
        LabeledField.__init__(self,xml)
        v = str(xml.firstChildElement())
        self.value = v.strip() == '1'
        
        
    def get_widget(self):
        self.w = gtk.CheckButton(label=None)
        self.w.set_active(self.value)
        return self.w
        
    
    def read_to_xml(self):
        value = '0'
        if self.w.get_active():
            value = '1' 
        e = LabeledField.read_to_xml(self)
        e.addElement((None,'value'),content=value)
        return e

    
    
class TextSingle(LabeledField):
    def __init__(self,xml):
        LabeledField.__init__(self,xml)
        self.value = str(xml.firstChildElement())
        
    def get_widget(self):
        self.w= gtk.Entry()
        self.w.set_text(self.value)
        return self.w
    
    def read_to_xml(self):
        e = LabeledField.read_to_xml(self)
        e.addElement((None,'value'),content=self.w.get_text())
        return e


class ListSingle(LabeledField):
    def __init__(self,xml):
        LabeledField.__init__(self,xml)
        options = []
        for e in xml.elements():
            if e.name == 'option':
                options.append(str(e.firstChildElement()))
            elif e.name == 'value':
                self.value = str(e)
        if options == [] : #bug in openfire, pubsub#itemreply whitout <option/> elements
            self.options = [self.value]
        else:
            self.options = options
        
    def get_widget(self):
        self.w= gtk.combo_box_new_text()
        index = 0
        for option in self.options:
            self.w.append_text(option)
            if option == self.value:
                self.w.set_active(index)
            index = index+1
        return self.w
    
    def read_to_xml(self):
        e = LabeledField.read_to_xml(self)
        e.addElement((None,'value'),content=self.w.get_active_text())
        return e


class ListMulti(LabeledField):
    def __init__(self,xml):
        LabeledField.__init__(self,xml)
        values  = []
        options = []
        for e in xml.elements():
            if e.name == 'option':
                options.append(str(e.firstChildElement()))
            elif e.name == 'value':
                values.append(str(e))
        self.options = options
        self.values = values
        
    def get_widget(self):
        self.model = gtk.ListStore(str)
        self.w= gtk.TreeView(self.model)
        tree_selection = self.w.get_selection()
        tree_selection.set_mode(gtk.SELECTION_MULTIPLE)
        
        col = gtk.TreeViewColumn("",gtk.CellRendererText(),text=0)
        
        self.w.append_column(col)
        self.w.set_headers_visible(False)
        index = 0
        for option in self.options:
            self.model.append((option,))
        
        def fun(model, path, iter):
            if model.get_value(iter,0) in self.values:
                tree_selection.select_iter(iter)
        self.model.foreach(fun)
        
        return self.w
    
    def read_to_xml(self):
        e = LabeledField.read_to_xml(self)
        #e.addElement((None,'value'),content=self.w.get_active_text())
        return e


class JIDMulti(LabeledField):
    def __init__(self,xml):
        LabeledField.__init__(self,xml)
        self.xml = xml

        
    def get_widget(self):
        self.w= gtk.Entry()
        self.w.set_text('')
        return self.w
    
    
    def read_to_xml(self):  
        return self.xml  
    
    
    
def field_from_xml(xml):
    m = {"hidden" : HiddenField,
         "boolean" : BooleanField,
         "text-single" : TextSingle,
         'list-single' : ListSingle,
         'list-multi' : ListMulti,
         'jid-multi' : JIDMulti}
    try:
         return m[xml['type']](xml) 
    except KeyError:
        print "Type not found", xml['type'], xml.toXml()
        raise
