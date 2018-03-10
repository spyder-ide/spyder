# -*- coding: utf-8 -*-
# Copyright © QCrash - Colin Duquesnoy
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the implementation generated and adapted of the ui file
dlg_github_login.ui form of the QCrash Project

Took from the QCrash Project - Colin Duquesnoy
https://github.com/ColinDuquesnoy/QCrash
"""

from qtpy import QtCore, QtWidgets

from spyder.config.base import _

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(366, 248)
        Dialog.setMinimumSize(QtCore.QSize(350, 0))
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lbl_html = QtWidgets.QLabel(Dialog)
        self.lbl_html.setObjectName("lbl_html")
        self.verticalLayout.addWidget(self.lbl_html)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setContentsMargins(-1, 0, -1, -1)
        self.formLayout.setObjectName("formLayout")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.le_username = QtWidgets.QLineEdit(Dialog)
        self.le_username.setObjectName("le_username")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.le_username)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.le_password = QtWidgets.QLineEdit(Dialog)
        self.le_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.le_password.setObjectName("le_password")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.le_password)
        self.verticalLayout.addLayout(self.formLayout)
        self.bt_sign_in = QtWidgets.QPushButton(Dialog)
        self.bt_sign_in.setObjectName("bt_sign_in")
        self.verticalLayout.addWidget(self.bt_sign_in)

        
        Dialog.setWindowTitle(_("Sign in to github"))
        self.label_2.setText(_("Username:"))
        self.label_3.setText(_("Password: "))
        self.bt_sign_in.setText(_("Sign in"))

        QtCore.QMetaObject.connectSlotsByName(Dialog)
