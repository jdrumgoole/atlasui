Quick Start
===========

This guide will help you get started with AtlasUI quickly.

Web Interface
-------------

Starting the Server
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Start the web server
    atlasui-server

    # Or with custom host/port
    PORT=8080 atlasui-server

Then open your browser to http://localhost:8000

Using the Dashboard
^^^^^^^^^^^^^^^^^^^

The dashboard provides an overview of your Atlas resources:

* Project count and list
* Cluster status across projects
* Recent alerts
* Backup status

Command-Line Interface
----------------------

List Projects
^^^^^^^^^^^^^

.. code-block:: bash

    # List all projects
    atlasui projects list

    # List with pagination
    atlasui projects list --page 2 --limit 50

Get Project Details
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Get specific project
    atlasui projects get <project-id>

Manage Clusters
^^^^^^^^^^^^^^^

.. code-block:: bash

    # List clusters in a project
    atlasui clusters list <project-id>

    # Get cluster details
    atlasui clusters get <project-id> <cluster-name>

    # Get cluster details as JSON
    atlasui clusters get <project-id> <cluster-name> --json

    # Delete a cluster
    atlasui clusters delete <project-id> <cluster-name>

    # Delete without confirmation
    atlasui clusters delete <project-id> <cluster-name> --force

View Alerts
^^^^^^^^^^^

.. code-block:: bash

    # List alerts for a project
    atlasui alerts list <project-id>

Manage Backups
^^^^^^^^^^^^^^

.. code-block:: bash

    # List snapshots for a cluster
    atlasui backups list <project-id> <cluster-name>

    # Get backup schedule
    atlasui backups schedule <project-id> <cluster-name>

API Usage
---------

You can also use the Atlas client programmatically:

.. code-block:: python

    from atlasui.client import AtlasClient

    # Create client
    with AtlasClient() as client:
        # List projects
        projects = client.list_projects()
        print(projects)

        # Get a project
        project = client.get_project('project-id')
        print(project)

        # List clusters
        clusters = client.list_clusters('project-id')
        print(clusters)

        # Get a cluster
        cluster = client.get_cluster('project-id', 'cluster-name')
        print(cluster)

Next Steps
----------

* Read the full :doc:`api/index` documentation
* Learn about :doc:`cli/index` commands
* Explore :doc:`development` for contributing
