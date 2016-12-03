from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..authentication.decorators import superuser_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods

from .forms import VirtualMachineForm
from .models import VirtualMachine
from .helpers import call_api


@login_required
def list_view(request):
    vm_list = request.user.vms.all()
    if request.user.is_superuser:
        su_vm_list = VirtualMachine.objects.exclude(users=request.user)
    else:
        su_vm_list = None
    return render(request, "vms/list.html", {"vm_list": vm_list, "su_vm_list": su_vm_list})


@login_required
def info_view(request, vm_id):
    vm = get_object_or_404(VirtualMachine, id=vm_id)
    if not request.user.is_superuser and not vm.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    vm_state = call_api("container.state", name=str(vm.uuid))
    if vm_state == 0:
        vm_ips = call_api("container.ips", name=str(vm.uuid))[1]
    elif vm_state == 2:
        messages.error(request, "Virtual machine does not exist!")
        return redirect("vm_list")
    else:
        vm_ips = []

    return render(request, "vms/info.html", {"vm": vm, "vm_state": vm_state, "vm_ips": vm_ips})


@require_http_methods(["POST"])
@login_required
def start_view(request, vm_id):
    vm = get_object_or_404(VirtualMachine, id=vm_id)
    if not request.user.is_superuser and not vm.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    ret = call_api("container.power", state=1, name=str(vm.uuid))
    if ret == 0:
        messages.success(request, "Virtual machine started!")
    else:
        messages.error(request, "Failed to start virtual machine! ({})".format(ret))

    return redirect("vm_info", vm_id=vm_id)


@require_http_methods(["POST"])
@login_required
def stop_view(request, vm_id):
    vm = get_object_or_404(VirtualMachine, id=vm_id)
    if not request.user.is_superuser and not vm.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if call_api("container.power", state=0, name=str(vm.uuid)) == 0:
        messages.success(request, "Virtual machine stopped!")
    else:
        messages.error(request, "Failed to stop virtual machine!")

    return redirect("vm_info", vm_id=vm_id)


@require_http_methods(["POST"])
@login_required
def password_view(request, vm_id):
    vm = get_object_or_404(VirtualMachine, id=vm_id)
    if not request.user.is_superuser and not vm.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    ret = call_api("container.reset_root_password", name=str(vm.uuid))
    if ret[0] == 0:
        vm.password = ret[1]
        vm.save()
        messages.success(request, "Root password set!")
    else:
        messages.error(request, "Failed to set root password!")

    return redirect("vm_info", vm_id=vm_id)


@login_required
def delete_view(request, vm_id):
    vm = get_object_or_404(VirtualMachine, id=vm_id)
    if not request.user.is_superuser and not vm.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if request.method == "POST":
        if request.POST.get("confirm", None) == vm.name:
            ret = call_api("container.destroy", name=str(vm.uuid))
            if ret == 0:
                vm.delete()
                messages.success(request, "Virtual machine deleted!")
            else:
                messages.error(request, "Failed to delete VM! ({})".format(ret))
            return redirect("vm_list")
        else:
            messages.error(request, "Failed deletion confirmation!")

    return render(request, "vms/delete.html", {"vm": vm})


@superuser_required
def create_view(request):
    if request.method == "POST":
        form = VirtualMachineForm(request.POST)
        if form.is_valid():
            instance = form.save()
            if instance:
                messages.success(request, "Virtual machine created!")
            else:
                messages.error(request, "Failed to create virtual machine!")
            return redirect("vm_list")
    else:
        form = VirtualMachineForm()
    return render(request, "vms/create_vm.html", {"form": form})