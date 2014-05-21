"""
Created on 12 May 2014

@author: si
"""
from django.conf import settings
from django.utils import simplejson

from cauldron_toil import _CauldronForm

from pprint import pprint

class Cauldron(object):
    """
    Container and controller for a set of forms
    """
    form_set = [] # must be defined by each child class
    
    def __init__(self, current_form_name=None):

        if len(self.form_set) == 0:
            raise NotImplementedError("form_set must be populated by implementing classes")

        # re-project into more convenient internal structure
        self._form_set = {}
        for form in self.form_set:
            f = _CauldronForm(form)
            if f.form_name in self._form_set:
                raise Exception("Cauldron contains duplicate forms [%s]" % f.form_name)

            if f.form_name in settings.TEMP_DATA:
                f.set_values(settings.TEMP_DATA[f.form_name]['form_fields'])

            self._form_set[f.form_name] = f

        if current_form_name and current_form_name not in self._form_set:
            raise Exception("Unknown form")
        self._current_form_name = current_form_name


    @property
    def current_form(self):
        if self._current_form_name:
            # I am here
            return self._form_set[self._current_form_name]
        else:
            a_ready_form = self._get_ready_forms()[0]
            return self._form_set[a_ready_form.form_name]

    
    def _get_complete_forms(self):
        """
        @return: subset list of self._form_set of forms that have been filled in.
        
            TODO - think about whether to include forms that have fallen out of scope
            if the user has changed answers and therefore flow through the forms
        """
        # TODO
        pass
    
    def _get_ready_forms(self):
        """
        @return: subset list of self._form_set
        
        subset is a list of forms who's-
        (i) ingredients are ready (i.e. the form that creates the ingredient has finished
                                   OR has no ingredients )
          AND
        (ii) .ready() method returns True
          AND
        (iii) has not already been called
        """        
        # TODO
        ready = []
        for cauldron_form in self._form_set.itervalues():
            # len(cauldron_form.ingredients) == 0 and
            if cauldron_form.ready()\
            and not cauldron_form.is_complete():
                ready.append(cauldron_form)
        return ready
    
    def save(self):
        """
        save current form then re-calculate which other forms are now ready
        """

        # TODO - temp save data to memory that is persistent between requests
        

        fresh_ingredients = self._update_ingredients(self.current_form)        
        django_form = self.current_form.instance
        json = django_form.save_serialise()
        self.current_form.set_values(django_form.cleaned_data)
        form_name = self.current_form.form_name
        settings.TEMP_DATA[form_name] = { 'form_fields' : json,
                                          'resulting_ingredients' : fresh_ingredients
                                        }
    
    @property
    def next_form(self):
        ready_forms = self._get_ready_forms()
        return ready_forms[0]


    def _update_ingredients(self, current_cauldron_form):
        """
        update forms which depended on a value from the form which has just been saved
        @return: dict of short_ingedient_name => ingredient_value - just those needed by other forms
        """
        form_name = current_cauldron_form.form_name
        fresh_ingredients = {}
        for cauldron_form in self._form_set.itervalues():
            ingredients = cauldron_form.ingredients_required(form_name)
            for i in ingredients:
                fq_ingredient = "%s.%s" % (form_name, i)
                ready_ingredient = getattr(current_cauldron_form.instance, i)
                print "would populate %s with %s which eq. %s" % (cauldron_form.form_name, fq_ingredient, ready_ingredient)
                cauldron_form.set_ingredient(fq_ingredient, ready_ingredient)
                fresh_ingredients[i] = ready_ingredient
        return fresh_ingredients
                


class CauldronFormMixin(object):
    
    def ready(self):
        """
        Might be implemented by subclasses.
        @return bool: if form can be displayed i.e. form as is ready for user input
        """
        return True
    
    def is_complete(self):
        """
        @return None (unknown to form); True or False if this form has been completed by user
        
        @see: _CauldronForm.is_complete()
        """
        return None

    def build_form(self):
        """
        Might be implemented by subclasses.
        Builds anything needed prior to form being rendered. e.g. populates multiple choice fields
        """
        pass
    
    def save_serialise(self):
        """
        This is called by the parent Cauldron.
        @return: string of serialised fields from form. Currently uses json
        """
        json_string = simplejson.dumps(self.cleaned_data)
        return json_string
        