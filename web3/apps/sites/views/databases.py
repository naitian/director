import datetime

from subprocess import Popen, PIPE

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from raven.contrib.django.raven_compat.models import client

from ..helpers import run_as_site, create_config_files, demote
from ..database_helpers import delete_postgres_database, change_postgres_password, delete_mysql_database, change_mysql_password, list_tables
from ..models import Site, User
from ..forms import DatabaseForm


@login_required
def create_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied
    if request.method == "POST":
        try:
            form = DatabaseForm(request.user, request.POST, instance=site.database)
        except Site.database.RelatedObjectDoesNotExist:
            form = DatabaseForm(request.user, request.POST, initial={"site": site.id})
        if form.is_valid():
            instance = form.save()
            if instance:
                messages.success(request, "New database created!")
            else:
                messages.error(request, "Failed to create database!")
            return redirect("info_site", site_id=site.id)
    else:
        try:
            form = DatabaseForm(request.user, instance=site.database)
        except:
            form = DatabaseForm(request.user, initial={"site": site.id})
    context = {
        "form": form,
        "site": site
    }
    return render(request, "sites/create_database.html", context)


@login_required
def modify_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if not site.database:
        messages.error(request, "No database provisioned!")
        return redirect("info_site", site_id=site.id)

    return render(request, "sites/edit_database.html", {"site": site})


@login_required
def sql_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if not site.database:
        return HttpResponse("ERROR: no database provisioned", content_type="text/plain")

    sql = request.POST.get("sql", "")
    version = request.POST.get("version", False) is not False

    if sql.startswith("\\!"):
        return HttpResponse("feature disabled\n\n", content_type="text/plain")

    if site.database.category == "mysql":
        if version:
            ret, out, err = run_as_site(site, ["mysql", "--version"])
        else:
            ret, out, err = run_as_site(site, ["mysql", "--user={}".format(site.database.username),
                                               "--host=mysql1", site.database.db_name, "-e", sql], env={"MYSQL_PWD": site.database.password})
    else:
        if version:
            ret, out, err = run_as_site(site, ["psql", "--version"])
        else:
            ret, out, err = run_as_site(site, ["psql", str(site.database), "-c", sql], env={"SHELL": "/usr/sbin/nologin"})
    return HttpResponse(out + err, content_type="text/plain")


@login_required
def backup_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if not site.database:
        messages.error(request, "No database provisioned!")
        return redirect("info_site", site_id=site.id)

    return render(request, "sites/backup_database.html", {"site": site})


@login_required
def load_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if request.method != "POST":
        return redirect("backup_database", site_id=site.id)

    if not site.database:
        messages.error(request, "No database provisioned!")
        return redirect("info_site", site_id=site.id)

    sql_file = request.FILES.get("file", None)
    if not sql_file:
        messages.error(request, "You must upload a .sql file!")
        return redirect("backup_database", site_id=site.id)

    if site.database.category == "postgresql":
        proc = Popen(["psql", str(site.database)], preexec_fn=demote(
            site.user.id, site.group.id), cwd=site.path, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    elif site.database.category == "mysql":
        proc = Popen(["mysql", "-u", site.database.username, "--password={}".format(site.database.password), "-h", "mysql1", site.database.db_name], preexec_fn=demote(
            site.user.id, site.group.id), cwd=site.path, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    for chunk in sql_file.chunks():
        proc.stdin.write(chunk)

    out, err = proc.communicate()

    if proc.returncode == 0:
        messages.success(request, "Database import completed!")
    else:
        messages.error(request, "Database import failed!")
        client.captureMessage("Database import failed, ({}) - {} - {}".format(proc.returncode, out.decode("utf-8"), err.decode("utf-8")))

    return redirect("info_site", site_id=site.id)


@login_required
def dump_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if request.method != "POST":
        return redirect("backup_database", site_id=site.id)

    if not site.database:
        messages.error(request, "No database provisioned!")
        return redirect("info_site", site_id=site.id)

    if site.database.category == "postgresql":
        # --cluster 9.6/main fixes the server version mismatch error
        ret, out, err = run_as_site(site, ["pg_dump", "--cluster", "9.6/main", str(site.database)], timeout=60)
    elif site.database.category == "mysql":
        ret, out, err = run_as_site(
            site, ["mysqldump", "-u", site.database.username, "--password={}".format(site.database.password), "-h", "mysql1", site.database.db_name], timeout=60)

    if ret == 0:
        resp = HttpResponse(out, content_type="application/force-download")
        resp["Content-Disposition"] = "attachment; filename=dump{}.sql".format(datetime.datetime.now().strftime("%m%d%Y"))
        return resp
    else:
        messages.error(request, "Failed to export database!")
        client.captureMessage("Database export failed, ({}) - {} - {}".format(ret, out, err))

    return redirect("info_site", site_id=site.id)


@login_required
def delete_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    if not site.database:
        messages.error(request, "No database provisioned!")
        return redirect("info_site", site_id=site.id)

    if request.method == "POST":
        if not request.POST.get("confirm", None) == site.name:
            messages.error(request, "Delete confirmation failed!")
            return redirect("delete_database", site_id=site_id)
        if site.database:
            flag = False
            if site.database.category == "postgresql":
                flag = delete_postgres_database(site.database)
            elif site.database.category == "mysql":
                flag = delete_mysql_database(site.database)
            if not flag:
                messages.error(request, "Failed to delete database!")
                return redirect("info_site", site_id=site.id)
            site.database.delete()
            create_config_files(site)
            messages.success(request, "Database deleted!")
        else:
            messages.error(request, "Database doesn't exist!")
        return redirect("info_site", site_id=site.id)
    else:
        return render(request, "sites/delete_database.html", {
            "site": site,
            "tables": list_tables(site.database)
        })


@require_http_methods(["POST"])
@login_required
def regenerate_database_view(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if not request.user.is_superuser and not site.group.users.filter(id=request.user.id).exists():
        raise PermissionDenied

    site.database.password = User.objects.make_random_password(length=24)
    site.database.save()
    flag = True

    if site.database.category == "postgresql":
        flag = change_postgres_password(site.database)
    elif site.database.category == "mysql":
        flag = change_mysql_password(site.database)

    if flag:
        create_config_files(site)
        messages.success(request, "Database credentials regenerated!")
    else:
        messages.error(request, "Failed to regenerate database credentials!")
    return redirect("info_site", site_id=site.id)
