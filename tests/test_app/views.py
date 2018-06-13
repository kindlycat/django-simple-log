# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.transaction import atomic
from django.forms import inlineformset_factory
from django.views.generic import CreateView, DeleteView, UpdateView

from tests.test_app.models import RelatedModel, ThirdModel


class FormsetViewMixin(object):
    formset_class = None
    formset = None

    @atomic
    def dispatch(self, request, *args, **kwargs):
        # Test related
        if issubclass(self.model, ThirdModel):
            self.formset_class = inlineformset_factory(
                ThirdModel, RelatedModel, fields='__all__', extra=0
            )
        return super(FormsetViewMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(FormsetViewMixin, self).get_context_data()
        context['formset'] = self.formset
        return context

    def get_form(self, form_class=None):
        if self.formset_class:
            self.formset = self.formset_class(
                self.request.POST or None,
                self.request.FILES or None,
                instance=getattr(self, 'object', None),
            )
        return super(FormsetViewMixin, self).get_form(form_class)

    def form_valid(self, form):
        if self.formset:
            if self.formset.is_valid():
                result = super(FormsetViewMixin, self).form_valid(form)
                self.formset.instance = form.instance
                self.formset.save()
                return result
            return self.form_invalid(form)
        return super(FormsetViewMixin, self).form_valid(form)


class TestCreateView(FormsetViewMixin, CreateView):
    fields = '__all__'
    success_url = '.'
    template_name = 'form.html'


class TestUpdateView(FormsetViewMixin, UpdateView):
    fields = '__all__'
    success_url = '.'
    template_name = 'form.html'


class TestDeleteView(DeleteView):
    success_url = '.'
