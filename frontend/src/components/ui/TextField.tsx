import { useId, type InputHTMLAttributes, type ReactNode } from "react";

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  id?: string;
  label: string;
  hint?: string;
  error?: string;
  leadingIcon?: ReactNode;
  trailingAction?: ReactNode;
}

export function TextField({
  id,
  label,
  hint,
  error,
  leadingIcon,
  trailingAction,
  className = "",
  ...inputProps
}: TextFieldProps) {
  const generatedId = useId().replace(/:/g, "");
  const inputId = id ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className="field">
      <label className="field__label" htmlFor={inputId}>{label}</label>
      <div className={`field__control ${error ? "field__control--error" : ""}`}>
        {leadingIcon ? <span className="field__leading">{leadingIcon}</span> : null}
        <input
          id={inputId}
          className={`field__input ${className}`.trim()}
          aria-invalid={Boolean(error)}
          aria-describedby={errorId ?? hintId}
          {...inputProps}
        />
        {trailingAction ? <span className="field__trailing">{trailingAction}</span> : null}
      </div>
      {error ? <p className="field__error" id={errorId} role="alert">{error}</p> :
        hint ? <p className="field__hint" id={hintId}>{hint}</p> : null}
    </div>
  );
}
