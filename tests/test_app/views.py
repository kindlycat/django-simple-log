# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic import CreateView, UpdateView, DeleteView


class TestCreateView(CreateView):
    fields = '__all__'
    success_url = '.'
    template_name = 'form.html'


class TestUpdateView(UpdateView):
    fields = '__all__'
    success_url = '.'
    template_name = 'form.html'


class TestDeleteView(DeleteView):
    success_url = '.'
