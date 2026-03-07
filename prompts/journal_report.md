 I need you to edit our journal report and rebuild it. Integrate our style into this prompt. I want you to remove the decision column after Next Steps. The decision column in between Close and Thank should have the ability to add a decision instead of a checkbox. Remove Pipeline Breakdown in Reports. Whenever a checkbox is clicked, the box should be checked instead of having to log an event.
                                                                  ### Requirements                                                              

                                                                                

  **Component Location**: Create                                                

  `donor-crm-frontend/src/components/journal/JournalReport.tsx`                 

                                                                                

  **API Integration**:                                                          

  - Use the existing `journalsApi.getReport(journalId)` from `@/api/endpoints`  

  - Use React Query's `useQuery` hook with queryKey: `['journals', journalId,   

  'report']`                                                                    

  - The API returns a `JournalReport` type with this structure:                 

    ```typescript                                                               

    {                                                                           

      journal: {                                                                

        id: string;                                                             

        title: string;                                                          

        goalAmountCents: number;                                                

        goalDeadline: string | null;                                            

        status: 'ACTIVE' | 'ARCHIVED';                                          

      };                                                                        

      summary: {                                                                

        totalContacts: number;                                                  

        stalledContacts: number;                                                

        stageDistribution: Record<JournalStage | 'NONE', number>;               

        decisions: {                                                            

          pending: number;                                                      

          confirmed: number;                                                    

          declined: number;                                                     

          canceled: number;                                                     

          confirmedTotalCents: number;                                          

          confirmedMonthlyEquivalentCents: number;                              

        };                                                                      

        goalProgressPercent: number;                                            

        openNextSteps: number;                                                  

        overdueNextSteps: number;                                               

      };                                                                        

    }                                                                           

                                                                                

  Props Interface:                                                              

  interface JournalReportProps {                                                

    journalId: string;                                                          

  }                                                                             

                                                                                

  Layout & Styling                                                              

                                                                                

  Use Tailwind CSS for all styling. The report should have a space-y-6 container

   with these sections:                                                         

                                                                                

  1. Key Metrics Section                                                        

                                                                                

  - Grid layout: grid grid-cols-2 md:grid-cols-4 gap-4                          

  - Each card: bg-white p-4 rounded-lg border border-gray-200                   

  - Card structure:                                                             

    - Label: text-sm text-gray-500                                              

    - Value: text-2xl font-bold with appropriate color                          

    - Subtext: text-xs text-gray-400 mt-1                                       

                                                                                

  Four Cards:                                                                   

  1. Total Contacts                                                             

    - Value color: text-gray-900                                                

    - Shows: summary.totalContacts                                              

  2. With Decisions                                                             

    - Value color: text-gray-900                                                

    - Shows: Sum of all decision statuses (pending + confirmed + declined +     

  canceled)                                                                     

    - Subtext: Calculate response rate as (totalDecisions / totalContacts *     

  100).toFixed(0)%                                                              

    - Format: "X% response rate"                                                

  3. Confirmed                                                                  

    - Value color: text-green-600                                               

    - Shows: summary.decisions.confirmedTotalCents / 100 formatted as $X,XXX    

    - Subtext: goalProgressPercent.toFixed(0)% of $X,XXX goal                   

  4. Pending Decisions                                                          

    - Value color: text-yellow-600                                              

    - Shows: summary.decisions.pending                                          

    - Subtext: "awaiting confirmation"                                          

                                                                                

  2. Progress Toward Goal Section                                               

                                                                                

  - Container: bg-white p-6 rounded-lg border border-gray-200                   

  - Title: text-sm font-semibold text-gray-700 mb-4 - "Progress Toward Goal"    

  - Progress bar:                                                               

    - Outer bar: h-8 bg-gray-100 rounded-full overflow-hidden                   

    - Inner bar: h-full bg-green-500 transition-all duration-500 flex           

  items-center justify-end pr-2                                                 

    - Width: Math.min(100, progressPercent)%                                    

    - Show confirmed amount text inside bar (white text) only if progressPercent

   >= 15%                                                                       

  - Labels below bar:                                                           

    - Flex layout: flex justify-between mt-2 text-xs text-gray-500              

    - Left: "$0"                                                                

    - Right: "Goal: $X,XXX" (font-medium)                                       

  - Legend below:                                                               

    - Green dot: w-3 h-3 rounded bg-green-500 with label "Confirmed"            

                                                                                

  3. Charts Section                                                             

                                                                                

  - Grid: grid grid-cols-1 lg:grid-cols-2 gap-6                                 

  - Each chart container: bg-white p-6 rounded-lg border border-gray-200        

  - Chart title: text-sm font-semibold text-gray-700 mb-4                       

                                                                                

  Chart 1: Contacts by Stage (Bar Chart)                                        

  - Title: "Contacts by Stage"                                                  

  - Use Recharts: BarChart with ResponsiveContainer                             

  - Height: 250px                                                               

  - Data: Map over the 6 stages using STAGE_INFO from constants                 

  const stageData = (Object.keys(STAGE_INFO) as JournalStage[]).map((stage) =>  

  ({                                                                            

    name: STAGE_INFO[stage].shortLabel,                                         

    count: summary.stageDistribution[stage] || 0,                               

    fill: STAGE_COLORS[stage],                                                  

  }));                                                                          

  - Stage Colors (exact hex values):                                            

  const STAGE_COLORS: Record<JournalStage, string> = {                          

    CONTACT: '#60A5FA',    // blue-400                                          

    MEET: '#34D399',       // emerald-400                                       

    CLOSE: '#FBBF24',      // amber-400                                         

    DECISION: '#A78BFA',   // violet-400                                        

    THANK: '#F472B6',      // pink-400                                          

    NEXT_STEPS: '#38BDF8', // sky-400                                           

  };                                                                            

  - Chart config:                                                               

    - Margin: { top: 10, right: 10, left: -10, bottom: 0 }                      

    - CartesianGrid: strokeDasharray="3 3" stroke="#E5E7EB"                     

    - XAxis: dataKey="name" tick={{ fontSize: 12 }} stroke="#9CA3AF"            

    - YAxis: allowDecimals={false} tick={{ fontSize: 12 }} stroke="#9CA3AF"     

    - Bar: dataKey="count" radius={[4, 4, 0, 0]} with Cell for each entry       

    - Tooltip style: white bg, 1px gray border, 8px border-radius, 12px font    

                                                                                

  Chart 2: Decision Status (Pie/Donut Chart)                                    

  - Title: "Decision Status"                                                    

  - Use Recharts: PieChart with ResponsiveContainer                             

  - Height: 250px                                                               

  - Data: Map decision statuses, filter out zero values                         

  const decisionStatusCounts = {                                                

    PENDING: summary.decisions.pending,                                         

    CONFIRMED: summary.decisions.confirmed,                                     

    DECLINED: summary.decisions.declined,                                       

    CANCELED: summary.decisions.canceled,                                       

  };                                                                            

                                                                                

  const decisionData = (Object.keys(STATUS_COLORS) as DecisionStatus[])         

    .map((status) => ({                                                         

      name: status.charAt(0) + status.slice(1).toLowerCase(),                   

      value: decisionStatusCounts[status] || 0,                                 

      fill: STATUS_COLORS[status],                                              

    }))                                                                         

    .filter((d) => d.value > 0);                                                

  - Status Colors (exact hex values):                                           

  const STATUS_COLORS: Record<DecisionStatus, string> = {                       

    PENDING: '#FCD34D',   // yellow-300                                         

    CONFIRMED: '#4ADE80', // green-400                                          

    DECLINED: '#F87171',  // red-400                                            

    CANCELED: '#9CA3AF',  // gray-400                                           

  };                                                                            

  - Show empty state if no decisions: "No decisions recorded yet" in center     

  - Pie config:                                                                 

    - cx="50%" cy="50%"                                                         

    - innerRadius={60} outerRadius={90} (donut style)                           

    - paddingAngle={2}                                                          

    - dataKey="value"                                                           

    - Label: label={({ name, value }) => \${name}: ${value}}`                   

    - labelLine={{ stroke: '#9CA3AF' }}                                         

  - Legend: verticalAlign="bottom" height={36} with small gray text formatter   

  - Tooltip: Same white style as bar chart                                      

                                                                                

  4. Alert Sections (Conditional)                                               

                                                                                

  Stalled Contacts Alert (only if summary.stalledContacts > 0):                 

  - Container: bg-orange-50 border border-orange-200 rounded-lg p-4             

  - Title: text-sm font-semibold text-orange-800 mb-1                           

    - Text: "X Stalled Contact" or "X Stalled Contacts" (singular/plural)       

  - Message: text-sm text-orange-700                                            

    - Text: "These contacts have not had activity in over 14 days. Consider     

  following up soon."                                                           

                                                                                

  Open Next Steps Alert (only if summary.openNextSteps > 0):                    

  - Container: bg-blue-50 border border-blue-200 rounded-lg p-4                 

  - Title: text-sm font-semibold text-blue-800 mb-1                             

    - Text: "X Open Next Step" or "X Open Next Steps" (singular/plural)         

  - Message: text-sm text-blue-700                                              

    - Text: "You have outstanding action items to complete."                    

                                                                                

  Loading State                                                                 

                                                                                

  if (isLoading) {                                                              

    return (                                                                    

      <div className="animate-pulse space-y-6">                                 

        <div className="grid grid-cols-4 gap-4">                                

          {[1, 2, 3, 4].map((i) => (                                            

            <div key={i} className="h-24 bg-gray-100 rounded-lg" />             

          ))}                                                                   

        </div>                                                                  

        <div className="h-64 bg-gray-100 rounded-lg" />                         

        <div className="h-64 bg-gray-100 rounded-lg" />                         

      </div>                                                                    

    );                                                                          

  }                                                                             

                                                                                

  Error State                                                                   

                                                                                

  if (!report) {                                                                

    return <p className="text-gray-500 text-center py-8">Unable to load         

  report</p>;                                                                   

  }                                                                             

                                                                                

  Dependencies Required                                                         

                                                                                

  - @tanstack/react-query - for useQuery                                        

  - recharts - for BarChart, PieChart, and all chart components                 

  - Import STAGE_INFO from ./constants                                          

  - Import types: JournalStage, DecisionStatus from @/api/types                 

  - Import journalsApi from @/api/endpoints                                     

                                                                                

  Important Notes                                                               

                                                                                

  1. Use exact hex color values - Don't use Tailwind classes for chart colors   

  2. Filter zero values from pie chart - Only show decision statuses with count 

  > 0                                                                           

  3. Calculate totals correctly - Sum all decision statuses for "With Decisions"

  4. Singular/plural handling - Check if count === 1 for alert titles           

  5. Currency formatting - Use .toLocaleString() for dollar amounts             

  6. Responsive design - 2-col on mobile, 4-col on desktop for metrics          

  7. Animation - Progress bar has transition-all duration-500                   

  8. Conditional rendering - Only show alerts if their counts > 0               

                                                                                

  Verification                                                                  

                                                                                

  After creating the component:                                                 

  1. The layout should match exactly with 4 metrics cards, progress bar, 2      

  charts, and conditional alerts                                                

  2. Colors should be vibrant and match the specified hex values                

  3. All data should come from the API report endpoint                          

  4. Loading state should show skeleton placeholders                            

  5. Charts should be interactive with tooltips on hover                        

  6. The component should be responsive across all screen sizes 