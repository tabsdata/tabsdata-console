def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        if input_id == "ext-input":
            self._handle_port("ext", event.input, require_diff=False)
        elif input_id == "int-input":
            self._handle_port("int", event.input, require_diff=True)
        elif input_id == "instance-input":
            self._handle_instance_name_submitted(event.input)

    # ---------------------------
    # Shared port flow
    # ---------------------------

    def _handle_port(self, kind: str, port_input: Input, require_diff: bool) -> None:
        """
        kind: "ext" or "int"
        require_diff: True for internal port, which must differ from arg_ext.
        """
        error_label = self.query_one(f"#{kind}-error", Label)
        confirm_label = self.query_one(f"#{kind}-confirm", Label)

        error_label.update("")
        confirm_label.update("")

        # Current value on instance, e.g. arg_ext or arg_int
        current_value = getattr(self.instance, f"arg_{kind}", None)

        value = port_input.value.strip()
        if value == "":
            value = current_value

        if not validate_port(value):
            error_label.update("That is not a valid port number. Please enter 1–65535.")
            self.set_focus(port_input)
            port_input.clear()
            return

        port = int(value)

        # Internal must not equal external
        if (
            require_diff
            and self.instance.arg_ext is not None
            and port == self.instance.arg_ext
        ):
            error_label.update(
                "Internal port must not be the same as external port. "
                "Please choose another port."
            )
            self.set_focus(port_input)
            port_input.clear()
            return

        in_use_by = port_in_use(
            app=self.app,
            port=port,
            current_instance_name=self.instance.name,
        )

        if in_use_by is not None:
            error_label.update(
                f"Port {port} is already in use by instance '{in_use_by}'. "
                "Please choose a different port."
            )
            self.set_focus(port_input)
            port_input.clear()
            return

        # Valid, distinct, and free
        setattr(self.instance, f"arg_{kind}", port)
        confirm_label.update(
            Text(
                f"Selected {'external' if kind == 'ext' else 'internal'} port: {port}",
                style="bold #22c55e",
            )
        )

        # If we just set external, reveal internal inputs
        if kind == "ext":
            self.query_one("#int-label", Label).display = True
            self.query_one("#int-input", Input).display = True
            self.query_one("#int-error", Label).display = True
            self.query_one("#int-confirm", Label).display = True
            self.set_focus(self.query_one("#int-input", Input))
        else:
            # Done with both ports, return instance to app
            self.app.handle_api_response(self, self.instance)

    # ---------------------------
    # Instance Name flow
    # ---------------------------

    def _handle_instance_name_submitted(self, instance_input: Input) -> None:
        instance_error = self.query_one("#instance-error", Label)
        instance_confirm = self.query_one("#instance-confirm", Label)

        instance_error.update("")
        instance_confirm.update("")

        value = instance_input.value.strip() or "tabsdata"

        if name_in_use(self.app, value):
            instance_error.update("That Name is Already in Use. Please Try Another:")
            self.set_focus(instance_input)
            instance_input.clear()
            return

        # Valid and free
        self.instance.name = value
        instance_confirm.update(
            Text(
                f"Defined an Instance with the following Name: {value}",
                style="bold #22c55e",
            )
        )

        # Reveal external port step and move focus there
        self.query_one("#title", Label).display = True
        self.query_one("#ext-label", Label).display = True
        self.query_one("#ext-input", Input).display = True
        self.query_one("#ext-error", Label).display = True
        self.query_one("#ext-confirm", Label).display = True

        self.set_focus(self.query_one("#ext-input", Input))