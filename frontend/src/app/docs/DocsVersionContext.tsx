"use client";

import { createContext, useContext } from "react";

export const DocsVersionContext = createContext<string>("v2.2.0");

export function useDocsVersion() {
	return useContext(DocsVersionContext);
}
