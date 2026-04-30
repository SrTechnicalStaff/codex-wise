; =============================================================================
; Codex Wise - Dart symbol, import, and call queries
; tree-sitter-language-pack dart grammar
; =============================================================================

; ---------------------------------------------------------------------------
; Symbols
; ---------------------------------------------------------------------------

(class_definition
  name: (identifier) @symbol.name
) @symbol.def

(mixin_declaration
  name: (identifier) @symbol.name
) @symbol.def

(enum_declaration
  name: (identifier) @symbol.name
) @symbol.def

(extension_declaration
  name: (identifier) @symbol.name
) @symbol.def

(function_signature
  name: (identifier) @symbol.name
  (formal_parameter_list) @symbol.params
) @symbol.def

(constructor_signature
  name: (identifier) @symbol.name
  parameters: (formal_parameter_list) @symbol.params
) @symbol.def

; ---------------------------------------------------------------------------
; Imports
; ---------------------------------------------------------------------------

(library_import
  (import_specification
    (configurable_uri
      (uri
        (string_literal) @import.module
      )
    )
  )
) @import.statement

; ---------------------------------------------------------------------------
; Calls
; ---------------------------------------------------------------------------

; Simple function/constructor call: foo(args)
(_
  (identifier) @call.target
  .
  (selector
    (argument_part
      (arguments) @call.arguments
    )
  )
) @call.site

; Method/static call: receiver.method(args)
(_
  (identifier) @call.receiver
  .
  (selector
    (unconditional_assignable_selector
      (identifier) @call.target
    )
  )
  .
  (selector
    (argument_part
      (arguments) @call.arguments
    )
  )
) @call.site
