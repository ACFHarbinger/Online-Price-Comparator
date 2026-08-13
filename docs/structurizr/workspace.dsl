workspace "Python-Module-Template" "C4 model for Python-Module-Template Python repository." {

    model {
        user = person "User" "Interacts with the Python application."

        system = softwareSystem "Python-Module-Template" "Python repository application." {
            cli = container "CLI Executable" "Command-line interface." "Python 3.11"
            lib = container "Core Package" "Python domain logic." "Python 3.11"
        }

        user -> system.cli "Executes CLI commands"
        system.cli -> system.lib "Uses"
    }

    views {
        systemContext system "SystemContext" {
            include *
            autoLayout lr
        }

        container system "Containers" {
            include *
            autoLayout lr
        }

        theme default
    }
}
