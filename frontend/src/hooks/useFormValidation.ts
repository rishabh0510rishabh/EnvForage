
// --- Advanced useFormValidation Hook ---
import { useState, useCallback, useEffect } from 'react';

// Simplified Zod interface mock to avoid direct dependency in this snippet
interface ZodSchemaMock<T> {
  safeParse: (data: unknown) => { success: true; data: T } | { success: false; error: { issues: { path: (string | number)[]; message: string }[] } };
}

export interface FormValidationState<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isValid: boolean;
  isDirty: boolean;
  isSubmitting: boolean;
}

/**
 * A highly advanced, Zod-powered form validation hook.
 * Replaces the need for massive libraries like Formik or react-hook-form
 * for mid-sized forms.
 * 
 * Features:
 * - Syncs validation against a Zod schema
 * - Tracks 'touched' state so errors only show after a user blurs an input
 * - Tracks 'dirty' state to warn users before navigating away
 * - Auto-validates on change, but only shows errors for touched fields
 * 
 * @param initialValues The starting values for the form
 * @param validationSchema A Zod schema (or similar object with a safeParse method)
 * @param onSubmit Callback triggered when form is perfectly valid and submitted
 */
export function useFormValidation<T extends Record<string, unknown>>(
  initialValues: T,
  validationSchema?: ZodSchemaMock<T>,
  onSubmit?: (values: T) => Promise<void> | void
) {
  const [state, setState] = useState<FormValidationState<T>>({
    values: initialValues,
    errors: {},
    touched: {},
    isValid: true, // Optimistic init
    isDirty: false,
    isSubmitting: false,
  });

  // Run validation engine whenever values change
  const validate = useCallback((currentValues: T) => {
    if (!validationSchema) return {};

    const result = validationSchema.safeParse(currentValues);
    if (result.success) {
      return {};
    }

    // Extract Zod errors into a flat dictionary map
    const newErrors: Partial<Record<keyof T, string>> = {};
    if (result.error && result.error.issues) {
      result.error.issues.forEach((issue: { path: (string | number)[]; message: string }) => {
        const key = issue.path[0] as keyof T;
        // Keep the first error for each field
        if (!newErrors[key]) {
          newErrors[key] = issue.message;
        }
      });
    }
    return newErrors;
  }, [validationSchema]);

  // Effect to re-validate on value changes
  useEffect(() => {
    const errors = validate(state.values);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState((prev) => ({
      ...prev,
      errors,
      isValid: Object.keys(errors).length === 0,
    }));
  }, [state.values, validate]);

  // Standard input onChange handler
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const finalValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;
    
    setState((prev) => ({
      ...prev,
      values: { ...prev.values, [name]: finalValue },
      isDirty: true,
    }));
  }, []);

  // Standard input onBlur handler (marks field as touched so errors appear)
  const handleBlur = useCallback((e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name } = e.target;
    setState((prev) => ({
      ...prev,
      touched: { ...prev.touched, [name]: true },
    }));
  }, []);

  // Programmatic setter for complex custom inputs (e.g. date pickers)
  const setFieldValue = useCallback((name: keyof T, value: unknown) => {
    setState((prev) => ({
      ...prev,
      values: { ...prev.values, [name]: value },
      isDirty: true,
      touched: { ...prev.touched, [name]: true },
    }));
  }, []);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      if (e) e.preventDefault();

      // Force all fields to be touched so all errors display
      const allTouched = Object.keys(state.values).reduce((acc, key) => {
        acc[key as keyof T] = true;
        return acc;
      }, {} as Partial<Record<keyof T, boolean>>);

      const errors = validate(state.values);
      const isValid = Object.keys(errors).length === 0;

      setState((prev) => ({
        ...prev,
        touched: allTouched,
        errors,
        isValid,
      }));

      if (isValid && onSubmit) {
        setState((prev) => ({ ...prev, isSubmitting: true }));
        try {
          await onSubmit(state.values);
        } finally {
          setState((prev) => ({ ...prev, isSubmitting: false }));
        }
      }
    },
    [state.values, validate, onSubmit]
  );

  const resetForm = useCallback(() => {
    setState({
      values: initialValues,
      errors: {},
      touched: {},
      isValid: true,
      isDirty: false,
      isSubmitting: false,
    });
  }, [initialValues]);

  return {
    ...state,
    handleChange,
    handleBlur,
    setFieldValue,
    handleSubmit,
    resetForm,
    // Helper to extract the specific error string only if the field is touched
    getFieldError: (name: keyof T) => (state.touched[name] ? state.errors[name] : undefined),
  };
}
