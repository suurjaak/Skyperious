Running in Vagrant
==================

Pre-requisites:

- [Virtualbox](https://www.virtualbox.org/) 4.0 or greater.
- [Vagrant](http://www.vagrantup.com/) 1.4 or greater.

Clone this project and get it running:

```
   git clone https://github.com/suurjaak/Skyperious
   cd Skyperious/packaging
   vagrant up
```

A `vagrant up` will do the following:

- download a default vagrant box with Ubuntu precise32 (no GUI)
- install Ubuntu desktop environment
- install Skyperious and its dependencies

#### Steps for using the Vagrantfile:

1. `vagrant up`
2. A VirtualBox window will appear
3. Wait until `vagrant up` finishes setting up the VM
4. Log into the console as the user `vagrant`, password `vagrant`
5. Run `startx -- :1`
6. Now you are in ubuntu desktop env
7. Open a terminal
8. `cd /vagrant`
9. `./skyperious.sh &`

To have your Skype DB files accessible within the VM, place them in project directory.

---

Vagrant support provided by [Alberto Scotto](https://github.com/alb-i986) 
and [Elan Ruusamäe](https://github.com/glensc).
