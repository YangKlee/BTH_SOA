# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models



class Users(models.Model):
    userid = models.TextField(db_column='UserId', primary_key=True)  # Field name made lowercase.
    lastname = models.TextField(db_column='LastName', blank=True, null=True)  # Field name made lowercase.
    firstname = models.TextField(db_column='FirstName', blank=True, null=True)  # Field name made lowercase.
    gender = models.IntegerField(db_column='Gender', blank=True, null=True)  # Field name made lowercase.
    dateofbirth = models.TextField(db_column='DateOfBirth', blank=True, null=True)  # Field name made lowercase.
    password = models.TextField(db_column='Password')  # Field name made lowercase.
    email = models.TextField(db_column='Email', unique=True)  # Field name made lowercase.
    phone = models.TextField(db_column='Phone', unique=True)  # Field name made lowercase.
    role = models.IntegerField(db_column='Role')  # Field name made lowercase.
    status = models.IntegerField(db_column='Status', blank=True, null=True)  # Field name made lowercase.
    createdat = models.TextField(db_column='CreatedAt', blank=True, null=True)  # Field name made lowercase.
    updatedat = models.TextField(db_column='UpdatedAt', blank=True, null=True)  # Field name made lowercase.

    @property
    def is_authenticated(self):
        return True

    class Meta:
        managed = False
        db_table = 'Users'

