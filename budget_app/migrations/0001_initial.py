# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountOwner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('fraction', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
            ],
            options={
                'ordering': ['subaccount'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BudgetLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=40)),
                ('has_subaccounts', models.BooleanField(default=False)),
                ('amount_available', models.DecimalField(max_digits=10, decimal_places=2)),
            ],
            options={
                'ordering': ['code'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CreditCard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('checked', models.BooleanField(default=False)),
                ('encumbered', models.BooleanField(default=False)),
                ('future_expense', models.BooleanField(default=False)),
                ('description', models.CharField(max_length=50)),
                ('date', models.DateField()),
                ('extra_note', models.TextField(null=True, blank=True)),
            ],
            options={
                'ordering': ['-date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExpenseBudgetLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('debit_or_credit', models.IntegerField(default=-1, choices=[(-1, b'Debit'), (1, b'Credit')])),
                ('budget_line', models.ForeignKey(related_name='expense_budget_line', to='budget_app.BudgetLine')),
                ('expense', models.ForeignKey(related_name='expense_budget_line', to='budget_app.Expense')),
            ],
            options={
                'ordering': ['-expense__date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FiscalYear',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('begin_on', models.DateField()),
                ('end_on', models.DateField()),
            ],
            options={
                'ordering': ['begin_on'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('note', models.TextField()),
                ('year', models.ForeignKey(related_name='notes', blank=True, to='budget_app.FiscalYear', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('nickname', models.CharField(max_length=50, blank=True)),
                ('home_phone', models.CharField(max_length=20, blank=True)),
                ('cell_phone', models.CharField(max_length=20, blank=True)),
                ('work_phone', models.CharField(max_length=20, blank=True)),
            ],
            options={
                'verbose_name_plural': 'people',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DepartmentMember',
            fields=[
                ('person_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='budget_app.Person')),
                ('position', models.CharField(max_length=8, choices=[(b'Inst', b'Instructor'), (b'Adj', b'Adjunct Professor'), (b'Asst', b'Assistant Professor'), (b'Assoc', b'Associate Professor'), (b'Full', b'Professor'), (b'Staff', b'Staff')])),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
            },
            bases=('budget_app.person',),
        ),
        migrations.CreateModel(
            name='SubAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
                ('abbrev', models.CharField(max_length=30)),
                ('amount_available', models.DecimalField(max_digits=10, decimal_places=2)),
                ('fiscal_year', models.ForeignKey(related_name='subaccounts', to='budget_app.FiscalYear')),
                ('owned_by', models.ManyToManyField(related_name='subaccounts', null=True, through='budget_app.AccountOwner', to='budget_app.DepartmentMember', blank=True)),
            ],
            options={
                'ordering': ['abbrev'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserPreferences',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('view_checked_only', models.BooleanField(default=False)),
                ('view_encumbrances_only', models.BooleanField(default=False)),
                ('view_future_only', models.BooleanField(default=False)),
                ('fiscal_year_to_view', models.ForeignKey(related_name='user_preferences', to='budget_app.FiscalYear')),
                ('user', models.ForeignKey(related_name='user_preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='expensebudgetline',
            name='subaccount',
            field=models.ForeignKey(related_name='expense_budget_line', blank=True, to='budget_app.SubAccount', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='expense',
            name='charged_by',
            field=models.ForeignKey(related_name='expense', blank=True, to='budget_app.DepartmentMember', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='expense',
            name='credit_card',
            field=models.ForeignKey(related_name='expense', blank=True, to='budget_app.CreditCard', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditcard',
            name='person',
            field=models.ForeignKey(related_name='credit_card', to='budget_app.DepartmentMember'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='budgetline',
            name='department',
            field=models.ForeignKey(related_name='budget_lines', to='budget_app.Department', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='budgetline',
            name='fiscal_year',
            field=models.ForeignKey(related_name='budget_lines', to='budget_app.FiscalYear'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='accountowner',
            name='department_member',
            field=models.ForeignKey(related_name='account_owners', to='budget_app.DepartmentMember'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='accountowner',
            name='subaccount',
            field=models.ForeignKey(related_name='account_owners', to='budget_app.SubAccount'),
            preserve_default=True,
        ),
    ]
